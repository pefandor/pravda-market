/**
 * Batch Withdrawal Script for Operator
 *
 * Processes pending withdrawal requests from the backend API
 * and sends them as a batch transaction to the Escrow contract.
 *
 * Usage:
 *   cd contracts
 *   OPERATOR_MNEMONIC="..." BACKEND_URL="https://..." ADMIN_TOKEN="..." npx ts-node scripts/batchWithdraw.ts
 *
 * Environment variables:
 *   OPERATOR_MNEMONIC - 24-word mnemonic for operator wallet
 *   BACKEND_URL - Backend API URL (e.g., https://pravda-market-production.up.railway.app)
 *   ADMIN_TOKEN - Admin authentication token
 *   MAX_BATCH_SIZE - Maximum withdrawals per batch (default: 50)
 *   DRY_RUN - Set to "true" to simulate without sending (default: false)
 */

import { WalletContractV4, internal } from '@ton/ton';
import { mnemonicToPrivateKey } from '@ton/crypto';
import { Address, beginCell, toNano, fromNano, external, storeMessage, SendMode } from '@ton/core';

// Configuration from environment
const OPERATOR_MNEMONIC = process.env.OPERATOR_MNEMONIC || '';
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || '';
const MAX_BATCH_SIZE = parseInt(process.env.MAX_BATCH_SIZE || '50');
const DRY_RUN = process.env.DRY_RUN === 'true';

// Contract configuration
const ESCROW_ADDRESS = 'kQCCEQCxcKFt89YFL5qa3Hc_nwV7vRxhHtvLcXhdM34Fmmhy';
const OPERATOR_WITHDRAW_OPCODE = 0x00000002;

// TonCenter testnet API
const TONCENTER_TESTNET = 'https://testnet.toncenter.com/api/v2';

// Daily limit from contract (10,000 TON)
const DAILY_LIMIT_NANOTON = 10_000_000_000_000n;

interface PendingWithdrawal {
    id: number;
    user_id: number;
    telegram_id: number;
    ton_address: string;
    amount_nanoton: number;
    amount_ton: number;
    created_at: string;
}

interface ContractState {
    totalDeposits: bigint;
    isPaused: boolean;
    dailyLimit: bigint;
    dailyWithdrawn: bigint;
}

function sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ============================================================================
// Backend API Functions
// ============================================================================

async function fetchPendingWithdrawals(): Promise<PendingWithdrawal[]> {
    const response = await fetch(`${BACKEND_URL}/admin/withdrawals/pending?limit=${MAX_BATCH_SIZE}`, {
        headers: {
            'Authorization': `Bearer ${ADMIN_TOKEN}`,
            'Content-Type': 'application/json',
        },
    });

    if (!response.ok) {
        throw new Error(`Backend error: ${response.status} - ${await response.text()}`);
    }

    return await response.json();
}

async function markAsProcessing(ids: number[]): Promise<void> {
    const response = await fetch(`${BACKEND_URL}/admin/withdrawals/process`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${ADMIN_TOKEN}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ids }),
    });

    if (!response.ok) {
        throw new Error(`Backend error: ${response.status} - ${await response.text()}`);
    }
}

async function markAsCompleted(ids: number[], txHash: string): Promise<void> {
    const response = await fetch(`${BACKEND_URL}/admin/withdrawals/complete`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${ADMIN_TOKEN}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ids, tx_hash: txHash }),
    });

    if (!response.ok) {
        throw new Error(`Backend error: ${response.status} - ${await response.text()}`);
    }
}

async function markAsFailed(ids: number[]): Promise<void> {
    const response = await fetch(`${BACKEND_URL}/admin/withdrawals/fail`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${ADMIN_TOKEN}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ids }),
    });

    if (!response.ok) {
        console.error(`Failed to mark withdrawals as failed: ${response.status}`);
    }
}

// ============================================================================
// TonCenter API Functions
// ============================================================================

async function callTonCenterApi(
    method: string,
    params: Record<string, string> = {},
    usePost = false
): Promise<any> {
    const url = `${TONCENTER_TESTNET}/${method}`;

    const options: RequestInit = usePost
        ? {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params),
        }
        : { method: 'GET' };

    const finalUrl = usePost
        ? url
        : `${url}?${new URLSearchParams(params).toString()}`;

    const response = await fetch(finalUrl, options);
    if (!response.ok) {
        const text = await response.text();
        throw new Error(`TonCenter error: ${response.status} - ${text}`);
    }
    const data = await response.json();
    if (!data.ok) {
        throw new Error(`TonCenter error: ${data.error || JSON.stringify(data)}`);
    }
    return data.result;
}

async function getContractState(): Promise<ContractState> {
    const result = await callTonCenterApi('runGetMethod', {
        address: ESCROW_ADDRESS,
        method: 'get_contract_state',
        stack: JSON.stringify([])
    }, true);

    if (!result.stack || result.stack.length < 5) {
        throw new Error('Invalid contract state response');
    }

    const parseStackValue = (item: any): bigint => {
        if (Array.isArray(item)) {
            return BigInt(item[1]);
        }
        return BigInt(item);
    };

    return {
        totalDeposits: parseStackValue(result.stack[0]),
        isPaused: parseStackValue(result.stack[1]) !== 0n,
        dailyLimit: parseStackValue(result.stack[2]),
        dailyWithdrawn: parseStackValue(result.stack[3]),
    };
}

// ============================================================================
// Main Script
// ============================================================================

async function main() {
    console.log('========================================');
    console.log('Pravda Escrow - Batch Withdrawal Script');
    console.log('========================================\n');

    // Validate environment
    if (!OPERATOR_MNEMONIC) {
        console.error('ERROR: OPERATOR_MNEMONIC not set');
        process.exit(1);
    }
    if (!ADMIN_TOKEN) {
        console.error('ERROR: ADMIN_TOKEN not set');
        process.exit(1);
    }

    console.log(`Backend URL: ${BACKEND_URL}`);
    console.log(`Max Batch Size: ${MAX_BATCH_SIZE}`);
    console.log(`Dry Run: ${DRY_RUN}`);
    console.log('');

    // Step 1: Fetch pending withdrawals
    console.log('Step 1: Fetching pending withdrawals...');
    const pendingWithdrawals = await fetchPendingWithdrawals();

    if (pendingWithdrawals.length === 0) {
        console.log('\n✅ No pending withdrawals. Exiting.');
        return;
    }

    console.log(`Found ${pendingWithdrawals.length} pending withdrawal(s):\n`);

    let totalAmountNanoton = 0n;
    for (const w of pendingWithdrawals) {
        console.log(`  #${w.id}: ${w.amount_ton.toFixed(4)} TON → ${w.ton_address.slice(0, 12)}...`);
        totalAmountNanoton += BigInt(w.amount_nanoton);
    }
    console.log(`\nTotal: ${fromNano(totalAmountNanoton)} TON`);

    // Step 2: Check contract state
    console.log('\nStep 2: Checking contract state...');
    await sleep(1500);
    const state = await getContractState();

    console.log(`  Total Deposits: ${fromNano(state.totalDeposits)} TON`);
    console.log(`  Daily Limit: ${fromNano(state.dailyLimit)} TON`);
    console.log(`  Daily Withdrawn: ${fromNano(state.dailyWithdrawn)} TON`);
    console.log(`  Paused: ${state.isPaused}`);

    if (state.isPaused) {
        console.error('\n❌ Contract is paused. Cannot process withdrawals.');
        process.exit(1);
    }

    const remainingDailyLimit = state.dailyLimit - state.dailyWithdrawn;
    if (totalAmountNanoton > remainingDailyLimit) {
        console.error(`\n❌ Total exceeds daily limit. Remaining: ${fromNano(remainingDailyLimit)} TON`);
        console.log('Reduce batch size or wait for daily reset.');
        process.exit(1);
    }

    // Step 3: Load operator wallet
    console.log('\nStep 3: Loading operator wallet...');
    const mnemonicArray = OPERATOR_MNEMONIC.split(' ');
    const keyPair = await mnemonicToPrivateKey(mnemonicArray);

    const wallet = WalletContractV4.create({
        publicKey: keyPair.publicKey,
        workchain: 0,
    });

    console.log(`  Operator Wallet: ${wallet.address.toString()}`);

    // Check wallet balance
    await sleep(1500);
    const walletInfo = await callTonCenterApi('getAddressInformation', {
        address: wallet.address.toString()
    });

    const walletBalance = BigInt(walletInfo.balance || '0');
    console.log(`  Wallet Balance: ${fromNano(walletBalance)} TON`);

    const requiredGas = toNano('0.5'); // 0.5 TON for gas
    if (walletBalance < requiredGas) {
        console.error(`\n❌ Insufficient gas. Need at least 0.5 TON`);
        process.exit(1);
    }

    // Get seqno
    await sleep(1500);
    let seqno = 0;
    if (walletInfo.state === 'active') {
        const seqnoResult = await callTonCenterApi('runGetMethod', {
            address: wallet.address.toString(),
            method: 'seqno',
            stack: JSON.stringify([])
        }, true);
        if (seqnoResult.stack && seqnoResult.stack.length > 0) {
            const item = seqnoResult.stack[0];
            seqno = parseInt(Array.isArray(item) ? item[1] : item, 16);
        }
    }
    console.log(`  Seqno: ${seqno}`);

    if (DRY_RUN) {
        console.log('\n⚠️  DRY RUN - Not sending transaction');
        console.log('\nWould process:');
        for (const w of pendingWithdrawals) {
            console.log(`  #${w.id}: ${w.amount_ton.toFixed(4)} TON → ${w.ton_address}`);
        }
        return;
    }

    // Step 4: Mark as processing
    console.log('\nStep 4: Marking withdrawals as processing...');
    const ids = pendingWithdrawals.map(w => w.id);
    await markAsProcessing(ids);
    console.log(`  Marked ${ids.length} withdrawal(s) as processing`);

    // Step 5: Build and send transaction
    console.log('\nStep 5: Building batch withdrawal transaction...');

    try {
        // Build operator_withdraw message body
        let bodyBuilder = beginCell()
            .storeUint(OPERATOR_WITHDRAW_OPCODE, 32)
            .storeUint(pendingWithdrawals.length, 16);

        for (const w of pendingWithdrawals) {
            const recipientAddress = Address.parse(w.ton_address);
            bodyBuilder = bodyBuilder
                .storeAddress(recipientAddress)
                .storeCoins(BigInt(w.amount_nanoton))
                .storeUint(BigInt(w.id), 64);
        }

        const messageBody = bodyBuilder.endCell();

        // Create internal message to escrow
        const escrowAddress = Address.parse(ESCROW_ADDRESS);
        const internalMessage = internal({
            to: escrowAddress,
            value: toNano('0.3'), // 0.3 TON for processing (will be refunded)
            body: messageBody,
        });

        // Create wallet transfer
        const transfer = wallet.createTransfer({
            seqno,
            secretKey: keyPair.secretKey,
            messages: [internalMessage],
            sendMode: SendMode.PAY_GAS_SEPARATELY,
        });

        // Wrap in external message
        const externalMessage = external({
            to: wallet.address,
            body: transfer,
        });

        const boc = beginCell()
            .store(storeMessage(externalMessage))
            .endCell()
            .toBoc()
            .toString('base64');

        console.log('  Transaction built successfully');
        console.log(`  BOC size: ${boc.length} bytes`);

        // Send transaction
        console.log('\nStep 6: Sending transaction...');
        await sleep(1500);

        const sendResult = await callTonCenterApi('sendBocReturnHash', {
            boc: boc
        }, true);

        const txHash = sendResult.hash || 'unknown';
        console.log(`  ✅ Transaction sent!`);
        console.log(`  Hash: ${txHash}`);

        // Step 7: Mark as completed
        console.log('\nStep 7: Marking withdrawals as completed...');
        await markAsCompleted(ids, txHash);
        console.log(`  ✅ Marked ${ids.length} withdrawal(s) as completed`);

        // Summary
        console.log('\n========================================');
        console.log('Summary');
        console.log('========================================');
        console.log(`Processed: ${pendingWithdrawals.length} withdrawal(s)`);
        console.log(`Total Amount: ${fromNano(totalAmountNanoton)} TON`);
        console.log(`Transaction Hash: ${txHash}`);
        console.log(`Explorer: https://testnet.tonscan.org/tx/${txHash}`);
        console.log('\n✅ Batch withdrawal completed successfully!');

    } catch (error) {
        console.error('\n❌ Transaction failed:', error);
        console.log('\nMarking withdrawals as failed...');
        await markAsFailed(ids);
        process.exit(1);
    }
}

main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
});
