/**
 * Minimal Testnet Deployment - Single API call approach
 */

import { TonClient, WalletContractV4, internal } from '@ton/ton';
import { mnemonicToWalletKey } from '@ton/crypto';
import { toNano, Cell, beginCell, storeStateInit } from '@ton/core';
import { Escrow, EscrowConfig, DEFAULT_EMERGENCY_DELAY } from './wrappers/Escrow';
import { readFileSync } from 'fs';

async function main() {
    const DEPLOY_MNEMONIC = process.env.DEPLOY_MNEMONIC;
    if (!DEPLOY_MNEMONIC) {
        console.log('DEPLOY_MNEMONIC not set');
        return;
    }

    // Parse mnemonic and create wallet
    const mnemonic = DEPLOY_MNEMONIC.split(' ');
    const keypair = await mnemonicToWalletKey(mnemonic);
    const deployWallet = WalletContractV4.create({
        workchain: 0,
        publicKey: keypair.publicKey,
    });

    console.log(`Wallet: ${deployWallet.address.toString({ testOnly: true })}`);

    // Load contract code
    const codeHex = readFileSync('./build/Escrow.compiled.json', 'utf-8');
    const { hex } = JSON.parse(codeHex);
    const code = Cell.fromBoc(Buffer.from(hex, 'hex'))[0];

    // Create escrow with wallet as operator/multisig
    const config: EscrowConfig = {
        operator: deployWallet.address,
        multisig: deployWallet.address,
        dailyLimit: toNano('10000'),
        emergencyDelay: DEFAULT_EMERGENCY_DELAY,
    };
    const escrow = Escrow.createFromConfig(config, code);
    console.log(`Contract: ${escrow.address.toString({ testOnly: true })}`);

    // Create client with longer timeout
    const client = new TonClient({
        endpoint: 'https://testnet.toncenter.com/api/v2/jsonRPC',
        apiKey: process.env.TONCENTER_API_KEY,
    });

    // Try to get seqno with delay before each call
    console.log('\nWaiting 5s before first API call...');
    await new Promise(r => setTimeout(r, 5000));

    const walletContract = client.open(deployWallet);

    let seqno = 0;
    try {
        seqno = await walletContract.getSeqno();
        console.log(`Seqno: ${seqno}`);
    } catch (e: any) {
        if (e?.response?.status === 429) {
            console.log('Rate limited on seqno. Using seqno=0 (new wallet)');
            seqno = 0;
        } else {
            throw e;
        }
    }

    // Send deploy transaction immediately
    console.log('\nSending deploy transaction...');
    try {
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
        console.log('Transaction sent!');
    } catch (e: any) {
        if (e?.response?.status === 429) {
            console.log('\nRate limited during send.');
            console.log('The transaction might have been sent. Check explorer:');
        } else {
            throw e;
        }
    }

    console.log('\n========================================');
    console.log('CHECK THESE LINKS IN 30 SECONDS:');
    console.log('========================================');
    console.log(`\nContract: https://testnet.tonscan.org/address/${escrow.address.toString({ testOnly: true })}`);
    console.log(`\nWallet: https://testnet.tonscan.org/address/${deployWallet.address.toString({ testOnly: true })}`);
}

main().catch(console.error);
