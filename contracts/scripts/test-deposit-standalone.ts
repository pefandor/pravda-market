/**
 * Standalone Test Deposit Script
 *
 * Sends 0.1 TON to Escrow contract with telegram_id memo.
 * Uses sendBocReturnHash for minimal API calls.
 *
 * Usage:
 *   npx ts-node scripts/test-deposit-standalone.ts
 */

import { WalletContractV4, internal } from '@ton/ton';
import { mnemonicToPrivateKey } from '@ton/crypto';
import { Address, beginCell, toNano, fromNano, external, storeMessage } from '@ton/core';

// Configuration
const CONTRACT_ADDRESS = 'kQCCEQCxcKFt89YFL5qa3Hc_nwV7vRxhHtvLcXhdM34Fmmhy';
const DEPOSIT_AMOUNT = toNano('0.1');
const TELEGRAM_ID = 989007395n;
const DEPOSIT_OPCODE = 0x00000001;

// TonCenter testnet API
const TONCENTER_TESTNET = 'https://testnet.toncenter.com/api/v2';

// Testnet mnemonic from CLAUDE.md
const MNEMONIC = 'pink clip giggle loan lake salmon cloth spike spread eye super often visual that observe affair pretty arrive festival finish primary swear year real';

async function callApi(method: string, params: Record<string, string> = {}, usePost = false): Promise<any> {
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
        throw new Error(`API error: ${response.status} - ${text}`);
    }
    const data = await response.json();
    if (!data.ok) {
        throw new Error(`API error: ${data.error || JSON.stringify(data)}`);
    }
    return data.result;
}

async function main() {
    console.log('========================================');
    console.log('Pravda Escrow - Test Deposit');
    console.log('========================================\n');

    // Create wallet from mnemonic
    console.log('Loading wallet from mnemonic...');
    const mnemonicArray = MNEMONIC.split(' ');
    const keyPair = await mnemonicToPrivateKey(mnemonicArray);

    const wallet = WalletContractV4.create({
        publicKey: keyPair.publicKey,
        workchain: 0,
    });

    const walletAddress = wallet.address;
    console.log(`Wallet: ${walletAddress.toString()}`);

    // Get wallet info (single API call)
    console.log('\nGetting wallet info...');
    const walletInfo = await callApi('getAddressInformation', {
        address: walletAddress.toString()
    });

    const balance = BigInt(walletInfo.balance || '0');
    console.log(`Balance: ${fromNano(balance)} TON`);

    if (balance < DEPOSIT_AMOUNT + toNano('0.05')) {
        console.error('\nERROR: Insufficient balance');
        console.log('Need at least 0.15 TON');
        console.log('\nGet testnet TON: https://t.me/testgiver_ton_bot');
        return;
    }

    // Extract seqno from wallet state
    let seqno = 0;
    if (walletInfo.state === 'active') {
        // Get seqno via runGetMethod (POST)
        await sleep(1500); // Rate limit delay
        try {
            const seqnoResult = await callApi('runGetMethod', {
                address: walletAddress.toString(),
                method: 'seqno',
                stack: JSON.stringify([])
            }, true);
            if (seqnoResult.stack && seqnoResult.stack.length > 0) {
                // Format can be ["num", "0x1"] or [["num", "0x1"]]
                const entry = seqnoResult.stack[0];
                const seqnoValue = Array.isArray(entry) ? entry[1] : entry;
                seqno = typeof seqnoValue === 'string' && seqnoValue.startsWith('0x')
                    ? parseInt(seqnoValue, 16)
                    : parseInt(seqnoValue, 10);
            }
            console.log(`Seqno: ${seqno}`);
        } catch (e: any) {
            console.log('Could not get seqno via API, will try seqno=1');
            seqno = 1; // Wallet was active, likely has seqno >= 1
        }
    } else {
        console.log(`Seqno: ${seqno} (new wallet)`);
    }

    // Build deposit message body
    const depositBody = beginCell()
        .storeUint(DEPOSIT_OPCODE, 32)
        .storeUint(TELEGRAM_ID, 64)
        .endCell();

    const contractAddress = Address.parse(CONTRACT_ADDRESS);

    console.log('\n--- Transaction Details ---');
    console.log(`To:          ${CONTRACT_ADDRESS}`);
    console.log(`Amount:      ${fromNano(DEPOSIT_AMOUNT)} TON`);
    console.log(`Telegram ID: ${TELEGRAM_ID}`);

    // Create and sign transfer
    const transfer = wallet.createTransfer({
        seqno: seqno,
        secretKey: keyPair.secretKey,
        messages: [
            internal({
                to: contractAddress,
                value: DEPOSIT_AMOUNT,
                body: depositBody,
            }),
        ],
    });

    // Create external message
    const externalMessage = external({
        to: walletAddress,
        init: seqno === 0 ? wallet.init : undefined,
        body: transfer,
    });

    // Serialize to BOC
    const boc = beginCell()
        .store(storeMessage(externalMessage))
        .endCell()
        .toBoc()
        .toString('base64');

    // Send transaction
    console.log('\nSending transaction...');
    await sleep(1500); // Rate limit delay

    try {
        const result = await callApi('sendBocReturnHash', { boc }, true);

        console.log('\n========================================');
        console.log('TRANSACTION SENT!');
        console.log('========================================\n');
        console.log(`Hash: ${result.hash}`);

    } catch (e: any) {
        console.error('\nFailed to send:', e.message);
        console.log('\nRetrying in 3 seconds...');
        await sleep(3000);

        const result = await callApi('sendBocReturnHash', { boc }, true);
        console.log('\n========================================');
        console.log('TRANSACTION SENT (retry)!');
        console.log('========================================\n');
        console.log(`Hash: ${result.hash}`);
    }

    console.log('\n--- Verify on Explorer ---');
    console.log(`Contract: https://testnet.tonscan.org/address/${CONTRACT_ADDRESS}`);
    console.log(`Wallet:   https://testnet.tonscan.org/address/${walletAddress.toString()}`);
}

function sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
}

main().catch(console.error);
