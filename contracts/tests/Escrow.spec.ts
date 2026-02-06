/**
 * Pravda Escrow Contract Tests
 *
 * Unit tests using @ton/sandbox
 */

import { Blockchain, SandboxContract, TreasuryContract } from '@ton/sandbox';
import { Cell, toNano, Address } from '@ton/core';
import { compile } from '@ton/blueprint';
import {
    Escrow,
    EscrowConfig,
    Opcodes,
    ErrorCodes,
    MIN_DEPOSIT,
    GAS_RESERVE,
    DEFAULT_EMERGENCY_DELAY,
} from '../wrappers/Escrow';
import '@ton/test-utils';

describe('Escrow Contract', () => {
    let code: Cell;

    beforeAll(async () => {
        code = await compile('Escrow');
    });

    let blockchain: Blockchain;
    let deployer: SandboxContract<TreasuryContract>;
    let operator: SandboxContract<TreasuryContract>;
    let multisig: SandboxContract<TreasuryContract>;
    let user1: SandboxContract<TreasuryContract>;
    let user2: SandboxContract<TreasuryContract>;
    let escrow: SandboxContract<Escrow>;

    beforeEach(async () => {
        blockchain = await Blockchain.create();

        deployer = await blockchain.treasury('deployer');
        operator = await blockchain.treasury('operator');
        multisig = await blockchain.treasury('multisig');
        user1 = await blockchain.treasury('user1');
        user2 = await blockchain.treasury('user2');

        const config: EscrowConfig = {
            operator: operator.address,
            multisig: multisig.address,
            dailyLimit: toNano('10000'), // 10,000 TON daily limit
            emergencyDelay: DEFAULT_EMERGENCY_DELAY,
        };

        escrow = blockchain.openContract(
            Escrow.createFromConfig(config, code)
        );

        const deployResult = await escrow.sendDeploy(
            deployer.getSender(),
            toNano('1')
        );

        expect(deployResult.transactions).toHaveTransaction({
            from: deployer.address,
            to: escrow.address,
            deploy: true,
            success: true,
        });
    });

    // ========================================================================
    // DEPLOYMENT TESTS
    // ========================================================================

    describe('Deployment', () => {
        it('should deploy with correct initial state', async () => {
            const state = await escrow.getContractState();

            expect(state.totalDeposits).toBe(0n);
            expect(state.isPaused).toBe(false);
            expect(state.dailyLimit).toBe(toNano('10000'));
            expect(state.dailyWithdrawn).toBe(0n);
            expect(state.emergencyDelay).toBe(DEFAULT_EMERGENCY_DELAY);
        });

        it('should have correct operator and multisig', async () => {
            const opAddr = await escrow.getOperator();
            const msAddr = await escrow.getMultisig();

            expect(opAddr.equals(operator.address)).toBe(true);
            expect(msAddr.equals(multisig.address)).toBe(true);
        });
    });

    // ========================================================================
    // DEPOSIT TESTS
    // ========================================================================

    describe('Deposit', () => {
        it('should accept deposit with telegram_id memo', async () => {
            const telegramId = 123456789n;
            const depositAmount = toNano('10');
            const stateBefore = await escrow.getContractState();

            const result = await escrow.sendDeposit(
                user1.getSender(),
                depositAmount,
                telegramId
            );

            expect(result.transactions).toHaveTransaction({
                from: user1.address,
                to: escrow.address,
                success: true,
            });

            // Check total deposits increased
            const stateAfter = await escrow.getContractState();
            expect(stateAfter.totalDeposits).toBeGreaterThan(stateBefore.totalDeposits);

            // Verify deposit amount is approximately correct (deposit - gas reserve)
            const depositedAmount = stateAfter.totalDeposits - stateBefore.totalDeposits;
            const expectedDeposit = depositAmount - GAS_RESERVE;
            expect(depositedAmount).toBeGreaterThanOrEqual(expectedDeposit - toNano('0.01'));
            expect(depositedAmount).toBeLessThanOrEqual(expectedDeposit + toNano('0.01'));
        });

        it('should reject deposit below minimum', async () => {
            const smallDeposit = toNano('0.05'); // Below 0.1 TON minimum

            const result = await escrow.sendDeposit(
                user1.getSender(),
                smallDeposit,
                123n
            );

            expect(result.transactions).toHaveTransaction({
                from: user1.address,
                to: escrow.address,
                success: false,
                exitCode: ErrorCodes.amountTooSmall,
            });
        });

        it('should reject deposit when paused', async () => {
            // Pause contract
            await escrow.sendPause(multisig.getSender());

            const result = await escrow.sendDeposit(
                user1.getSender(),
                toNano('10'),
                123n
            );

            expect(result.transactions).toHaveTransaction({
                from: user1.address,
                to: escrow.address,
                success: false,
                exitCode: ErrorCodes.paused,
            });
        });

        it('should accumulate multiple deposits', async () => {
            const stateBefore = await escrow.getContractState();

            await escrow.sendDeposit(user1.getSender(), toNano('5'), 123n);
            const stateAfterFirst = await escrow.getContractState();

            await escrow.sendDeposit(user1.getSender(), toNano('3'), 123n);
            const stateAfterSecond = await escrow.getContractState();

            // Total deposits should increase after each deposit
            expect(stateAfterFirst.totalDeposits).toBeGreaterThan(stateBefore.totalDeposits);
            expect(stateAfterSecond.totalDeposits).toBeGreaterThan(stateAfterFirst.totalDeposits);

            // Total should be approximately (5 - 0.05) + (3 - 0.05) = 7.9 TON
            // Allow some variance for gas
            expect(stateAfterSecond.totalDeposits).toBeGreaterThanOrEqual(toNano('7.8'));
            expect(stateAfterSecond.totalDeposits).toBeLessThanOrEqual(toNano('8.0'));
        });
    });

    // ========================================================================
    // OPERATOR WITHDRAWAL TESTS
    // ========================================================================

    describe('Operator Withdrawal', () => {
        beforeEach(async () => {
            // Setup: deposit funds for users
            await escrow.sendDeposit(user1.getSender(), toNano('100'), 123n);
            await escrow.sendDeposit(user2.getSender(), toNano('50'), 456n);
        });

        it('should process single withdrawal', async () => {
            const withdrawAmount = toNano('10');
            const stateBefore = await escrow.getContractState();

            const result = await escrow.sendOperatorWithdraw(
                operator.getSender(),
                toNano('0.5'),
                [
                    {
                        recipient: user1.address,
                        amount: withdrawAmount,
                        referenceId: 1001n,
                    },
                ]
            );

            expect(result.transactions).toHaveTransaction({
                from: operator.address,
                to: escrow.address,
                success: true,
            });

            // Check that withdrawal message was sent to user
            expect(result.transactions).toHaveTransaction({
                from: escrow.address,
                to: user1.address,
                success: true,
            });

            // Check total deposits decreased by withdrawal amount
            const stateAfter = await escrow.getContractState();
            expect(stateAfter.totalDeposits).toBe(stateBefore.totalDeposits - withdrawAmount);
        });

        it('should process batch withdrawal', async () => {
            const result = await escrow.sendOperatorWithdraw(
                operator.getSender(),
                toNano('1'),
                [
                    { recipient: user1.address, amount: toNano('5'), referenceId: 1n },
                    { recipient: user2.address, amount: toNano('3'), referenceId: 2n },
                ]
            );

            expect(result.transactions).toHaveTransaction({
                from: operator.address,
                to: escrow.address,
                success: true,
            });
        });

        it('should reject withdrawal from non-operator', async () => {
            const result = await escrow.sendOperatorWithdraw(
                user1.getSender(), // Not operator!
                toNano('0.5'),
                [{ recipient: user1.address, amount: toNano('1'), referenceId: 1n }]
            );

            expect(result.transactions).toHaveTransaction({
                from: user1.address,
                to: escrow.address,
                success: false,
                exitCode: ErrorCodes.unauthorized,
            });
        });

        it('should reject withdrawal exceeding user balance', async () => {
            const result = await escrow.sendOperatorWithdraw(
                operator.getSender(),
                toNano('0.5'),
                [
                    {
                        recipient: user1.address,
                        amount: toNano('1000'), // More than deposited
                        referenceId: 1n,
                    },
                ]
            );

            expect(result.transactions).toHaveTransaction({
                from: operator.address,
                to: escrow.address,
                success: false,
                exitCode: ErrorCodes.insufficientFunds,
            });
        });

        it('should reject withdrawal when paused', async () => {
            await escrow.sendPause(multisig.getSender());

            const result = await escrow.sendOperatorWithdraw(
                operator.getSender(),
                toNano('0.5'),
                [{ recipient: user1.address, amount: toNano('1'), referenceId: 1n }]
            );

            expect(result.transactions).toHaveTransaction({
                from: operator.address,
                to: escrow.address,
                success: false,
                exitCode: ErrorCodes.paused,
            });
        });
    });

    // ========================================================================
    // EMERGENCY WITHDRAWAL TESTS
    // ========================================================================

    describe('Emergency Withdrawal', () => {
        beforeEach(async () => {
            await escrow.sendDeposit(user1.getSender(), toNano('10'), 123n);
        });

        it('should request emergency withdrawal', async () => {
            const result = await escrow.sendRequestEmergency(user1.getSender());

            expect(result.transactions).toHaveTransaction({
                from: user1.address,
                to: escrow.address,
                success: true,
            });

            // Verify by trying to request again - should fail with already_pending
            const secondResult = await escrow.sendRequestEmergency(user1.getSender());
            expect(secondResult.transactions).toHaveTransaction({
                from: user1.address,
                to: escrow.address,
                success: false,
                exitCode: ErrorCodes.alreadyPending,
            });
        });

        it('should reject duplicate emergency request', async () => {
            await escrow.sendRequestEmergency(user1.getSender());

            const result = await escrow.sendRequestEmergency(user1.getSender());

            expect(result.transactions).toHaveTransaction({
                from: user1.address,
                to: escrow.address,
                success: false,
                exitCode: ErrorCodes.alreadyPending,
            });
        });

        it('should reject emergency request with zero balance', async () => {
            // user2 has no deposits
            const result = await escrow.sendRequestEmergency(user2.getSender());

            expect(result.transactions).toHaveTransaction({
                from: user2.address,
                to: escrow.address,
                success: false,
                exitCode: ErrorCodes.insufficientFunds,
            });
        });

        it('should reject execute before delay expires', async () => {
            await escrow.sendRequestEmergency(user1.getSender());

            // Try to execute immediately
            const result = await escrow.sendExecuteEmergency(user1.getSender());

            expect(result.transactions).toHaveTransaction({
                from: user1.address,
                to: escrow.address,
                success: false,
                exitCode: ErrorCodes.emergencyNotReady,
            });
        });

        it('should execute emergency after delay', async () => {
            // Get initial state - user1 has deposit from beforeEach
            const stateBefore = await escrow.getContractState();
            expect(stateBefore.totalDeposits).toBeGreaterThan(0n);

            // Request emergency
            const requestResult = await escrow.sendRequestEmergency(user1.getSender());
            expect(requestResult.transactions).toHaveTransaction({
                from: user1.address,
                to: escrow.address,
                success: true,
            });

            // Fast forward time by 7 days + 1 hour (ensure past delay)
            blockchain.now = (blockchain.now ?? Math.floor(Date.now() / 1000)) + DEFAULT_EMERGENCY_DELAY + 3600;

            // Execute emergency withdrawal
            const result = await escrow.sendExecuteEmergency(user1.getSender());

            expect(result.transactions).toHaveTransaction({
                from: user1.address,
                to: escrow.address,
                success: true,
            });

            // Check that funds were sent to user
            expect(result.transactions).toHaveTransaction({
                from: escrow.address,
                to: user1.address,
                success: true,
            });

            // Total deposits should be zero after withdrawal
            const stateAfter = await escrow.getContractState();
            expect(stateAfter.totalDeposits).toBe(0n);
        });

        it('should cancel emergency request', async () => {
            await escrow.sendRequestEmergency(user1.getSender());

            const result = await escrow.sendCancelEmergency(user1.getSender());

            expect(result.transactions).toHaveTransaction({
                from: user1.address,
                to: escrow.address,
                success: true,
            });

            // Verify cancellation by requesting again - should succeed now
            const newRequestResult = await escrow.sendRequestEmergency(user1.getSender());
            expect(newRequestResult.transactions).toHaveTransaction({
                from: user1.address,
                to: escrow.address,
                success: true,
            });
        });
    });

    // ========================================================================
    // ADMIN (MULTISIG) TESTS
    // ========================================================================

    describe('Admin Operations', () => {
        it('should pause and unpause contract', async () => {
            // Pause
            await escrow.sendPause(multisig.getSender());
            let state = await escrow.getContractState();
            expect(state.isPaused).toBe(true);

            // Unpause
            await escrow.sendUnpause(multisig.getSender());
            state = await escrow.getContractState();
            expect(state.isPaused).toBe(false);
        });

        it('should reject pause from non-multisig', async () => {
            const result = await escrow.sendPause(user1.getSender());

            expect(result.transactions).toHaveTransaction({
                from: user1.address,
                to: escrow.address,
                success: false,
                exitCode: ErrorCodes.unauthorized,
            });
        });

        it('should change operator', async () => {
            const newOperator = user1.address;

            await escrow.sendSetOperator(
                multisig.getSender(),
                newOperator
            );

            const opAddr = await escrow.getOperator();
            expect(opAddr.equals(newOperator)).toBe(true);
        });

        it('should reject operator change from non-multisig', async () => {
            const result = await escrow.sendSetOperator(
                operator.getSender(), // Operator can't change itself
                user1.address
            );

            expect(result.transactions).toHaveTransaction({
                from: operator.address,
                to: escrow.address,
                success: false,
                exitCode: ErrorCodes.unauthorized,
            });
        });

        it('should change daily limit', async () => {
            const newLimit = toNano('5000');

            await escrow.sendSetDailyLimit(multisig.getSender(), newLimit);

            const state = await escrow.getContractState();
            expect(state.dailyLimit).toBe(newLimit);
        });
    });

    // ========================================================================
    // DAILY LIMIT TESTS
    // ========================================================================

    describe('Daily Limit', () => {
        beforeEach(async () => {
            // Setup with smaller daily limit for testing
            const config: EscrowConfig = {
                operator: operator.address,
                multisig: multisig.address,
                dailyLimit: toNano('100'), // 100 TON daily limit
            };

            escrow = blockchain.openContract(
                Escrow.createFromConfig(config, code)
            );

            await escrow.sendDeploy(deployer.getSender(), toNano('1'));
            await escrow.sendDeposit(user1.getSender(), toNano('500'), 123n);
        });

        it('should enforce daily withdrawal limit', async () => {
            // First withdrawal should succeed
            await escrow.sendOperatorWithdraw(
                operator.getSender(),
                toNano('0.5'),
                [{ recipient: user1.address, amount: toNano('50'), referenceId: 1n }]
            );

            // Second withdrawal should succeed (total 100)
            await escrow.sendOperatorWithdraw(
                operator.getSender(),
                toNano('0.5'),
                [{ recipient: user1.address, amount: toNano('50'), referenceId: 2n }]
            );

            // Third withdrawal should fail (would exceed 100)
            const result = await escrow.sendOperatorWithdraw(
                operator.getSender(),
                toNano('0.5'),
                [{ recipient: user1.address, amount: toNano('10'), referenceId: 3n }]
            );

            expect(result.transactions).toHaveTransaction({
                from: operator.address,
                to: escrow.address,
                success: false,
                exitCode: ErrorCodes.dailyLimitExceeded,
            });
        });

        it('should reset daily limit after day change', async () => {
            // Use up daily limit
            const firstWithdraw = await escrow.sendOperatorWithdraw(
                operator.getSender(),
                toNano('0.5'),
                [{ recipient: user1.address, amount: toNano('100'), referenceId: 1n }]
            );
            expect(firstWithdraw.transactions).toHaveTransaction({
                from: operator.address,
                to: escrow.address,
                success: true,
            });

            // Fast forward 1 day + 1 hour (ensure new day)
            blockchain.now = (blockchain.now ?? Math.floor(Date.now() / 1000)) + 86400 + 3600;

            // Should succeed on new day
            const result = await escrow.sendOperatorWithdraw(
                operator.getSender(),
                toNano('0.5'),
                [{ recipient: user1.address, amount: toNano('50'), referenceId: 2n }]
            );

            expect(result.transactions).toHaveTransaction({
                from: operator.address,
                to: escrow.address,
                success: true,
            });
        });
    });
});
