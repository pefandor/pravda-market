/**
 * Pravda Escrow Contract Wrapper
 *
 * TypeScript wrapper for interacting with the Escrow smart contract
 */

import {
    Address,
    beginCell,
    Cell,
    Contract,
    contractAddress,
    ContractProvider,
    Sender,
    SendMode,
    toNano,
    Dictionary,
    DictionaryValue,
} from '@ton/core';

// Op codes (must match escrow.fc)
export const Opcodes = {
    deposit: 0x00000001,
    operatorWithdraw: 0x00000002,
    requestEmergency: 0x00000003,
    executeEmergency: 0x00000004,
    cancelEmergency: 0x00000005,
    pause: 0x00000010,
    unpause: 0x00000011,
    setOperator: 0x00000012,
    setDailyLimit: 0x00000013,
};

// Error codes (must match escrow.fc)
export const ErrorCodes = {
    insufficientFunds: 101,
    unauthorized: 102,
    paused: 103,
    dailyLimitExceeded: 104,
    emergencyNotReady: 105,
    emergencyNotFound: 106,
    invalidMemo: 107,
    amountTooSmall: 108,
    alreadyPending: 109,
};

// Constants
export const MIN_DEPOSIT = toNano('0.1');
export const GAS_RESERVE = toNano('0.05');
export const FORWARD_GAS = toNano('0.01');
export const DEFAULT_EMERGENCY_DELAY = 604800; // 7 days in seconds

// Config for contract deployment
export type EscrowConfig = {
    operator: Address;
    multisig: Address;
    dailyLimit: bigint;
    emergencyDelay?: number;
};

// Withdrawal batch item
export type WithdrawalItem = {
    recipient: Address;
    amount: bigint;
    referenceId: bigint;
};

// Contract state returned by get_contract_state
export type ContractState = {
    totalDeposits: bigint;
    isPaused: boolean;
    dailyLimit: bigint;
    dailyWithdrawn: bigint;
    emergencyDelay: number;
};

// Emergency status returned by get_emergency_status
export type EmergencyStatus = {
    hasPending: boolean;
    unlockTime: number;
};

/**
 * Build initial data cell for contract deployment
 */
export function escrowConfigToCell(config: EscrowConfig): Cell {
    return beginCell()
        .storeAddress(config.operator)
        .storeAddress(config.multisig)
        .storeCoins(0) // total_deposits
        .storeUint(0, 1) // is_paused
        .storeCoins(config.dailyLimit)
        .storeCoins(0) // daily_withdrawn
        .storeUint(0, 32) // last_withdrawal_day
        .storeUint(config.emergencyDelay ?? DEFAULT_EMERGENCY_DELAY, 32)
        .storeDict(null) // pending_emergencies
        .storeDict(null) // user_balances
        .endCell();
}

/**
 * Escrow Contract Wrapper
 */
export class Escrow implements Contract {
    constructor(
        readonly address: Address,
        readonly init?: { code: Cell; data: Cell }
    ) {}

    /**
     * Create contract instance from config (for deployment)
     */
    static createFromConfig(config: EscrowConfig, code: Cell, workchain = 0) {
        const data = escrowConfigToCell(config);
        const init = { code, data };
        return new Escrow(contractAddress(workchain, init), init);
    }

    /**
     * Create contract instance from address (for interaction)
     */
    static createFromAddress(address: Address) {
        return new Escrow(address);
    }

    /**
     * Send deploy transaction
     */
    async sendDeploy(provider: ContractProvider, via: Sender, value: bigint) {
        await provider.internal(via, {
            value,
            sendMode: SendMode.PAY_GAS_SEPARATELY,
            body: beginCell().endCell(),
        });
    }

    // ========================================================================
    // USER OPERATIONS
    // ========================================================================

    /**
     * Deposit TON with telegram_id memo
     * @param telegramId - User's Telegram ID for backend reconciliation
     * @param value - Amount to deposit (must be >= MIN_DEPOSIT + GAS_RESERVE)
     */
    async sendDeposit(
        provider: ContractProvider,
        via: Sender,
        value: bigint,
        telegramId: bigint
    ) {
        await provider.internal(via, {
            value,
            sendMode: SendMode.PAY_GAS_SEPARATELY,
            body: beginCell()
                .storeUint(Opcodes.deposit, 32)
                .storeUint(telegramId, 64)
                .endCell(),
        });
    }

    /**
     * Request emergency withdrawal (starts 7-day timer)
     */
    async sendRequestEmergency(
        provider: ContractProvider,
        via: Sender,
        value: bigint = toNano('0.1')
    ) {
        await provider.internal(via, {
            value,
            sendMode: SendMode.PAY_GAS_SEPARATELY,
            body: beginCell()
                .storeUint(Opcodes.requestEmergency, 32)
                .endCell(),
        });
    }

    /**
     * Execute emergency withdrawal after 7-day delay
     */
    async sendExecuteEmergency(
        provider: ContractProvider,
        via: Sender,
        value: bigint = toNano('0.1')
    ) {
        await provider.internal(via, {
            value,
            sendMode: SendMode.PAY_GAS_SEPARATELY,
            body: beginCell()
                .storeUint(Opcodes.executeEmergency, 32)
                .endCell(),
        });
    }

    /**
     * Cancel pending emergency withdrawal
     */
    async sendCancelEmergency(
        provider: ContractProvider,
        via: Sender,
        value: bigint = toNano('0.05')
    ) {
        await provider.internal(via, {
            value,
            sendMode: SendMode.PAY_GAS_SEPARATELY,
            body: beginCell()
                .storeUint(Opcodes.cancelEmergency, 32)
                .endCell(),
        });
    }

    // ========================================================================
    // OPERATOR OPERATIONS
    // ========================================================================

    /**
     * Batch withdrawal (operator only)
     * @param withdrawals - Array of withdrawal items
     */
    async sendOperatorWithdraw(
        provider: ContractProvider,
        via: Sender,
        value: bigint,
        withdrawals: WithdrawalItem[]
    ) {
        if (withdrawals.length === 0 || withdrawals.length > 50) {
            throw new Error('Withdrawal batch must have 1-50 items');
        }

        let builder = beginCell()
            .storeUint(Opcodes.operatorWithdraw, 32)
            .storeUint(withdrawals.length, 16);

        for (const w of withdrawals) {
            builder = builder
                .storeAddress(w.recipient)
                .storeCoins(w.amount)
                .storeUint(w.referenceId, 64);
        }

        await provider.internal(via, {
            value,
            sendMode: SendMode.PAY_GAS_SEPARATELY,
            body: builder.endCell(),
        });
    }

    // ========================================================================
    // MULTISIG OPERATIONS
    // ========================================================================

    /**
     * Pause contract (multisig only)
     */
    async sendPause(
        provider: ContractProvider,
        via: Sender,
        value: bigint = toNano('0.05')
    ) {
        await provider.internal(via, {
            value,
            sendMode: SendMode.PAY_GAS_SEPARATELY,
            body: beginCell()
                .storeUint(Opcodes.pause, 32)
                .endCell(),
        });
    }

    /**
     * Unpause contract (multisig only)
     */
    async sendUnpause(
        provider: ContractProvider,
        via: Sender,
        value: bigint = toNano('0.05')
    ) {
        await provider.internal(via, {
            value,
            sendMode: SendMode.PAY_GAS_SEPARATELY,
            body: beginCell()
                .storeUint(Opcodes.unpause, 32)
                .endCell(),
        });
    }

    /**
     * Set new operator address (multisig only)
     */
    async sendSetOperator(
        provider: ContractProvider,
        via: Sender,
        newOperator: Address,
        value: bigint = toNano('0.05')
    ) {
        await provider.internal(via, {
            value,
            sendMode: SendMode.PAY_GAS_SEPARATELY,
            body: beginCell()
                .storeUint(Opcodes.setOperator, 32)
                .storeAddress(newOperator)
                .endCell(),
        });
    }

    /**
     * Set daily withdrawal limit (multisig only)
     */
    async sendSetDailyLimit(
        provider: ContractProvider,
        via: Sender,
        newLimit: bigint,
        value: bigint = toNano('0.05')
    ) {
        await provider.internal(via, {
            value,
            sendMode: SendMode.PAY_GAS_SEPARATELY,
            body: beginCell()
                .storeUint(Opcodes.setDailyLimit, 32)
                .storeCoins(newLimit)
                .endCell(),
        });
    }

    // ========================================================================
    // GET METHODS
    // ========================================================================

    /**
     * Get contract state
     */
    async getContractState(provider: ContractProvider): Promise<ContractState> {
        const result = await provider.get('get_contract_state', []);
        return {
            totalDeposits: result.stack.readBigNumber(),
            isPaused: result.stack.readNumber() !== 0,
            dailyLimit: result.stack.readBigNumber(),
            dailyWithdrawn: result.stack.readBigNumber(),
            emergencyDelay: result.stack.readNumber(),
        };
    }

    /**
     * Get user balance by address hash
     * @param addressHash - 256-bit hash of user address (use address.hash)
     */
    async getBalance(
        provider: ContractProvider,
        addressHash: bigint
    ): Promise<bigint> {
        const result = await provider.get('get_user_balance_by_hash', [
            { type: 'int', value: addressHash },
        ]);
        return result.stack.readBigNumber();
    }

    /**
     * Get user balance by address
     * Convenience method that computes hash automatically
     */
    async getBalanceByAddress(
        provider: ContractProvider,
        address: Address
    ): Promise<bigint> {
        const hash = BigInt('0x' + address.hash.toString('hex'));
        return this.getBalance(provider, hash);
    }

    /**
     * Get emergency withdrawal status
     * @param addressHash - 256-bit hash of user address
     */
    async getEmergencyStatus(
        provider: ContractProvider,
        addressHash: bigint
    ): Promise<EmergencyStatus> {
        const result = await provider.get('get_emergency_status', [
            { type: 'int', value: addressHash },
        ]);
        return {
            hasPending: result.stack.readNumber() !== 0,
            unlockTime: result.stack.readNumber(),
        };
    }

    /**
     * Get operator address
     */
    async getOperator(provider: ContractProvider): Promise<Address> {
        const result = await provider.get('get_operator', []);
        return result.stack.readAddress();
    }

    /**
     * Get multisig address
     */
    async getMultisig(provider: ContractProvider): Promise<Address> {
        const result = await provider.get('get_multisig', []);
        return result.stack.readAddress();
    }
}
