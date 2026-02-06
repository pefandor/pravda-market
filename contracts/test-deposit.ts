/**
 * Test Deposit Script
 * Sends a test deposit to the deployed Escrow contract
 *
 * Usage: DEPLOY_MNEMONIC="..." npx ts-node test-deposit.ts
 */

import { TonClient, WalletContractV4 } from '@ton/ton';
import { mnemonicToWalletKey } from '@ton/crypto';
import { toNano, Address, beginCell } from '@ton/core';
import { Escrow, Opcodes } from './wrappers/Escrow';

// Contract address (deployed on testnet)
const ESCROW_ADDRESS = 'kQCCEQCxcKFt89YFL5qa3Hc_nwV7vRxhHtvLcXhdM34Fmmhy';

// Deposit parameters
const DEPOSIT_AMOUNT = toNano('0.1'); // 0.1 TON
const TELEGRAM_ID = 989007395n;

async function main() {
    console.log('========================================');
    console.log('Test Deposit to Escrow Contract');
    console.log('========================================\n');

    const DEPLOY_MNEMONIC = process.env.DEPLOY_MNEMONIC;
    if (!DEPLOY_MNEMONIC) {
        console.log('DEPLOY_MNEMONIC not set');
        return;
    }

    // Create wallet from mnemonic
    const mnemonic = DEPLOY_MNEMONIC.split(' ');
    const keypair = await mnemonicToWalletKey(mnemonic);
    const wallet = WalletContractV4.create({
        workchain: 0,
        publicKey: keypair.publicKey,
    });

    console.log(`Wallet: ${wallet.address.toString({ testOnly: true })}`);

    // Connect to testnet
    const client = new TonClient({
        endpoint: 'https://testnet.toncenter.com/api/v2/jsonRPC',
    });

    const walletContract = client.open(wallet);

    // Get wallet balance
    const balance = await walletContract.getBalance();
    console.log(`Wallet balance: ${Number(balance) / 1e9} TON`);

    if (balance < DEPOSIT_AMOUNT + toNano('0.05')) {
        console.log('Insufficient balance for deposit + gas');
        return;
    }

    // Parse escrow address
    const escrowAddress = Address.parse(ESCROW_ADDRESS);
    console.log(`\nEscrow contract: ${escrowAddress.toString({ testOnly: true })}`);

    // Create escrow instance for reading state
    const escrow = client.open(Escrow.createFromAddress(escrowAddress));

    // Get contract state BEFORE deposit
    console.log('\n--- Contract State BEFORE Deposit ---');
    try {
        const stateBefore = await escrow.getContractState();
        console.log(`Total Deposits: ${Number(stateBefore.totalDeposits) / 1e9} TON`);
        console.log(`Is Paused: ${stateBefore.isPaused}`);
        console.log(`Daily Limit: ${Number(stateBefore.dailyLimit) / 1e9} TON`);
    } catch (e) {
        console.log('Could not read contract state (may be rate limited)');
    }

    // Build deposit message body
    // op::deposit = 0x00000001
    // telegram_id: uint64
    const depositBody = beginCell()
        .storeUint(Opcodes.deposit, 32) // op code
        .storeUint(TELEGRAM_ID, 64)     // telegram_id memo
        .endCell();

    console.log('\n--- Sending Deposit ---');
    console.log(`Amount: ${Number(DEPOSIT_AMOUNT) / 1e9} TON`);
    console.log(`Telegram ID: ${TELEGRAM_ID}`);

    // Get seqno and send
    const seqno = await walletContract.getSeqno();
    console.log(`Seqno: ${seqno}`);

    await walletContract.sendTransfer({
        secretKey: keypair.secretKey,
        seqno: seqno,
        messages: [
            {
                to: escrowAddress,
                value: DEPOSIT_AMOUNT,
                body: depositBody,
            },
        ],
    });

    console.log('\nTransaction sent! Waiting for confirmation...');

    // Wait for transaction to be processed
    await new Promise(resolve => setTimeout(resolve, 15000));

    // Get contract state AFTER deposit
    console.log('\n--- Contract State AFTER Deposit ---');
    try {
        const stateAfter = await escrow.getContractState();
        console.log(`Total Deposits: ${Number(stateAfter.totalDeposits) / 1e9} TON`);
        console.log(`Is Paused: ${stateAfter.isPaused}`);
    } catch (e) {
        console.log('Could not read contract state (may be rate limited)');
    }

    console.log('\n========================================');
    console.log('CHECK RESULTS:');
    console.log('========================================');
    console.log(`\nEscrow Contract:`);
    console.log(`https://testnet.tonscan.org/address/${escrowAddress.toString({ testOnly: true })}`);
    console.log(`\nYour Wallet:`);
    console.log(`https://testnet.tonscan.org/address/${wallet.address.toString({ testOnly: true })}`);
    console.log(`\nLook for a transaction with:`);
    console.log(`- Value: ~0.1 TON`);
    console.log(`- Op code: 0x00000001 (deposit)`);
    console.log(`- Memo: telegram_id = ${TELEGRAM_ID}`);
}

main().catch(console.error);
