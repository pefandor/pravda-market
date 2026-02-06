/**
 * Interact with Deployed Escrow Contract
 *
 * Usage:
 *   npx blueprint run interactEscrow --testnet
 *   npx blueprint run interactEscrow --mainnet
 */

import { toNano, Address } from '@ton/core';
import { NetworkProvider } from '@ton/blueprint';
import { Escrow } from '../wrappers/Escrow';

export async function run(provider: NetworkProvider) {
    // ========================================================================
    // CONFIGURATION
    // ========================================================================

    const CONTRACT_ADDRESS = process.env.ESCROW_CONTRACT_ADDRESS;
    if (!CONTRACT_ADDRESS) {
        throw new Error(
            'ESCROW_CONTRACT_ADDRESS environment variable is required.\n' +
            'Set it to your deployed escrow contract address.'
        );
    }

    // ========================================================================
    // CONNECT TO CONTRACT
    // ========================================================================

    console.log('========================================');
    console.log('Pravda Escrow Contract Interaction');
    console.log('========================================\n');

    const contractAddress = Address.parse(CONTRACT_ADDRESS);
    const escrow = provider.open(Escrow.createFromAddress(contractAddress));

    console.log(`Contract: ${contractAddress.toString()}\n`);

    // ========================================================================
    // READ STATE
    // ========================================================================

    console.log('--- Contract State ---');
    const state = await escrow.getContractState();
    console.log(`Total Deposits:    ${Number(state.totalDeposits) / 1e9} TON`);
    console.log(`Is Paused:         ${state.isPaused}`);
    console.log(`Daily Limit:       ${Number(state.dailyLimit) / 1e9} TON`);
    console.log(`Daily Withdrawn:   ${Number(state.dailyWithdrawn) / 1e9} TON`);
    console.log(`Emergency Delay:   ${state.emergencyDelay / 86400} days`);
    console.log('');

    console.log('--- Addresses ---');
    const operatorAddr = await escrow.getOperator();
    const multisigAddr = await escrow.getMultisig();
    console.log(`Operator: ${operatorAddr.toString()}`);
    console.log(`Multisig: ${multisigAddr.toString()}`);
    console.log('');

    // ========================================================================
    // INTERACTIVE MENU
    // ========================================================================

    console.log('--- Available Actions ---');
    console.log('1. Deposit TON (as user)');
    console.log('2. Check balance (by address)');
    console.log('3. Request emergency withdrawal');
    console.log('4. Execute emergency withdrawal');
    console.log('5. Pause contract (multisig only)');
    console.log('6. Unpause contract (multisig only)');
    console.log('');
    console.log('To execute an action, modify this script or use:');
    console.log('  npx blueprint run interactEscrow --testnet --action=deposit --amount=10 --telegram_id=123');
    console.log('');

    // ========================================================================
    // EXAMPLE ACTIONS (uncomment to use)
    // ========================================================================

    /*
    // Example: Deposit 1 TON with telegram_id
    console.log('Depositing 1 TON...');
    await escrow.sendDeposit(
        provider.sender(),
        toNano('1'),
        123456789n  // Your telegram_id
    );
    console.log('Deposit sent!');
    */

    /*
    // Example: Check balance for an address
    const userAddress = Address.parse('EQD...');
    const balance = await escrow.getBalanceByAddress(userAddress);
    console.log(`Balance: ${Number(balance) / 1e9} TON`);
    */

    /*
    // Example: Request emergency withdrawal
    console.log('Requesting emergency withdrawal...');
    await escrow.sendRequestEmergency(provider.sender());
    console.log('Emergency request sent! Wait 7 days to execute.');
    */

    /*
    // Example: Pause contract (multisig only)
    console.log('Pausing contract...');
    await escrow.sendPause(provider.sender());
    console.log('Contract paused!');
    */
}
