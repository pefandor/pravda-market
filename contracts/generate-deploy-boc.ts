/**
 * Generate Deployment BOC for Manual Submission
 *
 * This creates a deployment transaction that can be submitted via:
 * 1. Tonkeeper wallet (import BOC)
 * 2. TonScan (submit transaction)
 * 3. Any TON wallet that supports raw BOC
 */

import { WalletContractV4, internal } from '@ton/ton';
import { mnemonicToWalletKey } from '@ton/crypto';
import { toNano, Address, Cell, beginCell, storeStateInit } from '@ton/core';
import { Escrow, EscrowConfig, DEFAULT_EMERGENCY_DELAY } from './wrappers/Escrow';
import { readFileSync, writeFileSync } from 'fs';

async function main() {
    console.log('========================================');
    console.log('Generate Escrow Deployment BOC');
    console.log('========================================\n');

    const DEPLOY_MNEMONIC = process.env.DEPLOY_MNEMONIC;
    if (!DEPLOY_MNEMONIC) {
        console.log('DEPLOY_MNEMONIC not set');
        return;
    }

    // Parse mnemonic
    const mnemonic = DEPLOY_MNEMONIC.split(' ');
    const keypair = await mnemonicToWalletKey(mnemonic);
    const deployWallet = WalletContractV4.create({
        workchain: 0,
        publicKey: keypair.publicKey,
    });

    console.log(`Deploy wallet: ${deployWallet.address.toString({ testOnly: true })}`);

    // Load compiled contract
    const codeHex = readFileSync('./build/Escrow.compiled.json', 'utf-8');
    const { hex } = JSON.parse(codeHex);
    const code = Cell.fromBoc(Buffer.from(hex, 'hex'))[0];

    // Use deploy wallet for both operator and multisig (for testing)
    const operatorAddress = deployWallet.address;
    const multisigAddress = deployWallet.address;

    console.log('\nConfiguration:');
    console.log(`  Operator:     ${operatorAddress.toString({ testOnly: true })}`);
    console.log(`  Multisig:     ${multisigAddress.toString({ testOnly: true })}`);
    console.log(`  Daily Limit:  10000 TON`);
    console.log(`  Emergency:    7 days\n`);

    // Create escrow config
    const config: EscrowConfig = {
        operator: operatorAddress,
        multisig: multisigAddress,
        dailyLimit: toNano('10000'),
        emergencyDelay: DEFAULT_EMERGENCY_DELAY,
    };

    // Create contract instance
    const escrow = Escrow.createFromConfig(config, code);
    console.log(`Contract address: ${escrow.address.toString({ testOnly: true })}\n`);

    // Build state init
    const stateInit = escrow.init!;
    const stateInitCell = beginCell()
        .store(storeStateInit(stateInit))
        .endCell();
    const stateInitBoc = stateInitCell.toBoc().toString('base64');

    // Save state init for verification
    writeFileSync('./build/escrow-state-init.boc.b64', stateInitBoc);

    // For manual deployment, output key info
    console.log('========================================');
    console.log('DEPLOYMENT INFO');
    console.log('========================================\n');

    console.log('1. Contract Address (SAVE THIS):');
    console.log(`   ${escrow.address.toString({ testOnly: true })}\n`);

    console.log('2. Testnet Explorer Links:');
    console.log(`   https://testnet.tonscan.org/address/${escrow.address.toString({ testOnly: true })}`);
    console.log(`   https://testnet.tonviewer.com/${escrow.address.toString({ testOnly: true })}\n`);

    console.log('3. State Init BOC saved to: build/escrow-state-init.boc.b64\n');

    console.log('4. To deploy with Tonkeeper (TESTNET):');
    console.log('   a) Import wallet with mnemonic');
    console.log('   b) Send 0.5 TON to contract address with state init attached');
    console.log('   c) Or use this deep link:\n');

    const tonkeeperLink = `https://app.tonkeeper.com/transfer/${escrow.address.toString({ testOnly: true })}?amount=500000000&stateInit=${encodeURIComponent(stateInitBoc)}`;
    console.log(`   ${tonkeeperLink}\n`);

    console.log('========================================');
    console.log('QUICK DEPLOY (if rate limit is ok):');
    console.log('========================================');
    console.log('Wait 5+ minutes, then run:');
    console.log('DEPLOY_MNEMONIC="..." npx ts-node deploy-testnet.ts\n');
}

main().catch(console.error);
