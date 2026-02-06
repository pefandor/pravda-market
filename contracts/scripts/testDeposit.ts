/**
 * Test Deposit Script
 *
 * Sends a test deposit of 0.1 TON to the Escrow contract with telegram_id memo.
 *
 * Usage:
 *   npx blueprint run testDeposit --testnet
 */

import { toNano, Address, fromNano } from '@ton/core';
import { NetworkProvider } from '@ton/blueprint';
import { Escrow } from '../wrappers/Escrow';

// Testnet contract address from CLAUDE.md
const CONTRACT_ADDRESS = 'kQCCEQCxcKFt89YFL5qa3Hc_nwV7vRxhHtvLcXhdM34Fmmhy';

// Test parameters
const DEPOSIT_AMOUNT = toNano('0.1');
const TELEGRAM_ID = 989007395n;

export async function run(provider: NetworkProvider) {
    console.log('========================================');
    console.log('Pravda Escrow - Test Deposit');
    console.log('========================================\n');

    // Connect to contract
    const contractAddress = Address.parse(CONTRACT_ADDRESS);
    const escrow = provider.open(Escrow.createFromAddress(contractAddress));

    console.log(`Contract:    ${contractAddress.toString()}`);
    console.log(`Amount:      ${fromNano(DEPOSIT_AMOUNT)} TON`);
    console.log(`Telegram ID: ${TELEGRAM_ID}\n`);

    // Check contract state before deposit
    console.log('--- Contract State Before ---');
    try {
        const stateBefore = await escrow.getContractState();
        console.log(`Total Deposits: ${fromNano(stateBefore.totalDeposits)} TON`);
        console.log(`Is Paused:      ${stateBefore.isPaused}`);

        if (stateBefore.isPaused) {
            console.error('\nERROR: Contract is paused! Cannot deposit.');
            return;
        }
    } catch (e) {
        console.log('Could not read contract state (may not be deployed yet)');
    }
    console.log('');

    // Send deposit
    console.log('Sending deposit transaction...');
    console.log('(You will be prompted to confirm in your wallet)\n');

    await escrow.sendDeposit(
        provider.sender(),
        DEPOSIT_AMOUNT,
        TELEGRAM_ID
    );

    console.log('========================================');
    console.log('DEPOSIT TRANSACTION SENT!');
    console.log('========================================\n');

    console.log('Transaction submitted to the network.');
    console.log('Wait a few seconds for confirmation...\n');

    // Wait for transaction to be processed
    console.log('Waiting for transaction confirmation (10s)...');
    await sleep(10000);

    // Check contract state after deposit
    console.log('\n--- Contract State After ---');
    try {
        const stateAfter = await escrow.getContractState();
        console.log(`Total Deposits: ${fromNano(stateAfter.totalDeposits)} TON`);
    } catch (e) {
        console.log('Could not read contract state');
    }

    console.log('\n--- Next Steps ---');
    console.log('1. Check transaction on explorer:');
    console.log(`   https://testnet.tonscan.org/address/${CONTRACT_ADDRESS}`);
    console.log('2. Backend should detect this deposit via indexer');
    console.log('3. User balance should be credited for telegram_id:', TELEGRAM_ID.toString());
}

function sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
}
