/**
 * Deploy Escrow Contract to TON Blockchain
 *
 * Usage:
 *   npx blueprint run deployEscrow --testnet
 *   npx blueprint run deployEscrow --mainnet
 */

import { toNano, Address } from '@ton/core';
import { compile, NetworkProvider } from '@ton/blueprint';
import { Escrow, EscrowConfig, DEFAULT_EMERGENCY_DELAY } from '../wrappers/Escrow';

export async function run(provider: NetworkProvider) {
    // ========================================================================
    // CONFIGURATION - Update these values before deployment!
    // ========================================================================

    // Operator wallet - receives batch withdrawal authority
    // In production, use a secure wallet controlled by your backend
    const OPERATOR_ADDRESS = process.env.ESCROW_OPERATOR_ADDRESS;
    if (!OPERATOR_ADDRESS) {
        throw new Error(
            'ESCROW_OPERATOR_ADDRESS environment variable is required.\n' +
            'Set it to the address of your operator wallet.'
        );
    }

    // Multisig wallet - admin operations (pause, set limits, etc.)
    // In production, use a 2-of-3 multisig wallet
    const MULTISIG_ADDRESS = process.env.ESCROW_MULTISIG_ADDRESS;
    if (!MULTISIG_ADDRESS) {
        throw new Error(
            'ESCROW_MULTISIG_ADDRESS environment variable is required.\n' +
            'Set it to the address of your multisig wallet.'
        );
    }

    // Daily withdrawal limit (in TON)
    const DAILY_LIMIT_TON = process.env.ESCROW_DAILY_LIMIT || '10000';

    // ========================================================================
    // DEPLOYMENT
    // ========================================================================

    console.log('========================================');
    console.log('Pravda Escrow Contract Deployment');
    console.log('========================================\n');

    // Parse addresses
    const operatorAddress = Address.parse(OPERATOR_ADDRESS);
    const multisigAddress = Address.parse(MULTISIG_ADDRESS);
    const dailyLimit = toNano(DAILY_LIMIT_TON);

    console.log('Configuration:');
    console.log(`  Operator:     ${operatorAddress.toString()}`);
    console.log(`  Multisig:     ${multisigAddress.toString()}`);
    console.log(`  Daily Limit:  ${DAILY_LIMIT_TON} TON`);
    console.log(`  Emergency:    ${DEFAULT_EMERGENCY_DELAY / 86400} days\n`);

    // Compile contract
    console.log('Compiling contract...');
    const code = await compile('Escrow');
    console.log('Contract compiled successfully.\n');

    // Create config
    const config: EscrowConfig = {
        operator: operatorAddress,
        multisig: multisigAddress,
        dailyLimit: dailyLimit,
        emergencyDelay: DEFAULT_EMERGENCY_DELAY,
    };

    // Create contract instance
    const escrow = provider.open(Escrow.createFromConfig(config, code));

    console.log(`Contract address: ${escrow.address.toString()}`);
    console.log('');

    // Check if already deployed
    const isDeployed = await provider.isContractDeployed(escrow.address);
    if (isDeployed) {
        console.log('Contract is already deployed!');
        console.log('Use interactEscrow.ts to interact with it.');
        return;
    }

    // Deploy
    console.log('Deploying contract...');
    await escrow.sendDeploy(provider.sender(), toNano('0.5'));

    // Wait for deployment
    console.log('Waiting for deployment confirmation...');
    await provider.waitForDeploy(escrow.address);

    console.log('\n========================================');
    console.log('DEPLOYMENT SUCCESSFUL!');
    console.log('========================================\n');
    console.log(`Contract Address: ${escrow.address.toString()}`);
    console.log('');
    console.log('Next steps:');
    console.log('1. Save the contract address to your backend config');
    console.log('2. Fund the contract for gas reserves');
    console.log('3. Test deposits on testnet before mainnet');
    console.log('');

    // Verify deployment
    console.log('Verifying deployment...');
    const state = await escrow.getContractState();
    console.log(`  Total Deposits: ${state.totalDeposits} nanoTON`);
    console.log(`  Is Paused:      ${state.isPaused}`);
    console.log(`  Daily Limit:    ${state.dailyLimit} nanoTON`);
    console.log('');
    console.log('Deployment verified successfully!');
}
