/**
 * Direct Testnet Deployment Script
 * Bypasses blueprint's buggy script discovery
 *
 * Usage: npx ts-node deploy-testnet.ts
 */

import { TonClient, WalletContractV4, internal } from '@ton/ton';
import { mnemonicToWalletKey, mnemonicNew } from '@ton/crypto';
import { toNano, Address } from '@ton/core';
import { Escrow, EscrowConfig, DEFAULT_EMERGENCY_DELAY } from './wrappers/Escrow';
import { readFileSync } from 'fs';
import { Cell } from '@ton/core';
import { getHttpEndpoint } from '@orbs-network/ton-access';

async function main() {
    console.log('========================================');
    console.log('Pravda Escrow Contract - Testnet Deploy');
    console.log('========================================\n');

    // Configuration
    const OPERATOR_ADDRESS = process.env.ESCROW_OPERATOR_ADDRESS;
    const MULTISIG_ADDRESS = process.env.ESCROW_MULTISIG_ADDRESS;
    const DEPLOY_MNEMONIC = process.env.DEPLOY_MNEMONIC;
    const DAILY_LIMIT_TON = process.env.ESCROW_DAILY_LIMIT || '10000';

    if (!OPERATOR_ADDRESS) {
        console.log('ESCROW_OPERATOR_ADDRESS not set.');
        console.log('Generating test addresses for demo...\n');
    }

    if (!DEPLOY_MNEMONIC) {
        console.log('DEPLOY_MNEMONIC not set.');
        console.log('\nTo deploy, you need:');
        console.log('1. A TON wallet with testnet TON');
        console.log('2. Get testnet TON from: https://t.me/testgiver_ton_bot');
        console.log('3. Set DEPLOY_MNEMONIC="word1 word2 ... word24"');
        console.log('\nOr generate a new wallet:');

        // Generate new mnemonic for demo
        const newMnemonic = await mnemonicNew();
        const keypair = await mnemonicToWalletKey(newMnemonic);
        const wallet = WalletContractV4.create({
            workchain: 0,
            publicKey: keypair.publicKey,
        });

        console.log('\n--- NEW TEST WALLET ---');
        console.log('Mnemonic (SAVE THIS):');
        console.log(newMnemonic.join(' '));
        console.log(`\nWallet address: ${wallet.address.toString({ testOnly: true })}`);
        console.log('\nSteps:');
        console.log('1. Send 1+ TON from @testgiver_ton_bot to this address');
        console.log('2. Run again with: DEPLOY_MNEMONIC="<mnemonic>" npx ts-node deploy-testnet.ts');
        return;
    }

    // Parse mnemonic
    const mnemonic = DEPLOY_MNEMONIC.split(' ');
    if (mnemonic.length !== 24) {
        throw new Error('DEPLOY_MNEMONIC must be 24 words');
    }

    // Create wallet from mnemonic
    const keypair = await mnemonicToWalletKey(mnemonic);
    const deployWallet = WalletContractV4.create({
        workchain: 0,
        publicKey: keypair.publicKey,
    });

    console.log(`Deploy wallet: ${deployWallet.address.toString({ testOnly: true })}`);

    // Connect to testnet
    const endpoint = 'https://testnet.toncenter.com/api/v2/jsonRPC';
    console.log(`Using TonCenter testnet endpoint`);
    console.log('Rate limited? Try: TONCENTER_API_KEY=xxx npx ts-node deploy-testnet.ts\n');

    const apiKey = process.env.TONCENTER_API_KEY;
    const client = new TonClient({
        endpoint,
        apiKey: apiKey || undefined,
    });

    // Helper function with retry
    async function withRetry<T>(fn: () => Promise<T>, retries = 3, delay = 2000): Promise<T> {
        for (let i = 0; i < retries; i++) {
            try {
                return await fn();
            } catch (e: any) {
                if (e?.response?.status === 429 && i < retries - 1) {
                    console.log(`Rate limited, waiting ${delay / 1000}s...`);
                    await new Promise(r => setTimeout(r, delay));
                    delay *= 2; // exponential backoff
                } else {
                    throw e;
                }
            }
        }
        throw new Error('Max retries reached');
    }

    const walletContract = client.open(deployWallet);
    const balance = await withRetry(() => walletContract.getBalance());
    console.log(`Balance: ${Number(balance) / 1e9} TON\n`);

    if (balance < toNano('0.5')) {
        console.log('Insufficient balance! Need at least 0.5 TON');
        console.log('Get testnet TON from: https://t.me/testgiver_ton_bot');
        return;
    }

    // Use deploy wallet address for both operator and multisig if not specified
    const operatorAddress = OPERATOR_ADDRESS
        ? Address.parse(OPERATOR_ADDRESS)
        : deployWallet.address;
    const multisigAddress = MULTISIG_ADDRESS
        ? Address.parse(MULTISIG_ADDRESS)
        : deployWallet.address;

    console.log('Configuration:');
    console.log(`  Operator:     ${operatorAddress.toString({ testOnly: true })}`);
    console.log(`  Multisig:     ${multisigAddress.toString({ testOnly: true })}`);
    console.log(`  Daily Limit:  ${DAILY_LIMIT_TON} TON`);
    console.log(`  Emergency:    ${DEFAULT_EMERGENCY_DELAY / 86400} days\n`);

    // Load compiled contract
    const codeHex = readFileSync('./build/Escrow.compiled.json', 'utf-8');
    const { hex } = JSON.parse(codeHex);
    const code = Cell.fromBoc(Buffer.from(hex, 'hex'))[0];
    console.log('Contract code loaded from build/Escrow.compiled.json');

    // Create escrow config
    const config: EscrowConfig = {
        operator: operatorAddress,
        multisig: multisigAddress,
        dailyLimit: toNano(DAILY_LIMIT_TON),
        emergencyDelay: DEFAULT_EMERGENCY_DELAY,
    };

    // Create contract instance
    const escrow = Escrow.createFromConfig(config, code);
    console.log(`Contract address: ${escrow.address.toString({ testOnly: true })}\n`);

    // Check if already deployed
    const contractState = await withRetry(() => client.getContractState(escrow.address));
    if (contractState.state === 'active') {
        console.log('Contract is already deployed!');
        console.log(`Explorer: https://testnet.tonscan.org/address/${escrow.address.toString({ testOnly: true })}`);
        return;
    }

    // Deploy
    console.log('Deploying contract...');
    const seqno = await withRetry(() => walletContract.getSeqno());

    await walletContract.sendTransfer({
        secretKey: keypair.secretKey,
        seqno: seqno,
        messages: [
            internal({
                to: escrow.address,
                value: toNano('0.5'),
                init: escrow.init,
                body: undefined,
            }),
        ],
    });

    console.log('Transaction sent, waiting for confirmation...');

    // Wait for deployment
    let attempts = 0;
    while (attempts < 30) {
        await new Promise(resolve => setTimeout(resolve, 3000));
        const state = await withRetry(() => client.getContractState(escrow.address), 2, 3000);
        if (state.state === 'active') {
            console.log('\n========================================');
            console.log('DEPLOYMENT SUCCESSFUL!');
            console.log('========================================\n');
            console.log(`Contract Address: ${escrow.address.toString({ testOnly: true })}`);
            console.log(`\nTestnet Explorer:`);
            console.log(`https://testnet.tonscan.org/address/${escrow.address.toString({ testOnly: true })}`);
            console.log(`\nhttps://testnet.tonviewer.com/${escrow.address.toString({ testOnly: true })}`);
            return;
        }
        attempts++;
        process.stdout.write('.');
    }

    console.log('\nDeployment may be pending. Check explorer for status.');
    console.log(`https://testnet.tonscan.org/address/${escrow.address.toString({ testOnly: true })}`);
}

main().catch(console.error);
