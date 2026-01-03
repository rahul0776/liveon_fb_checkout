import { BlobServiceClient, ContainerClient } from "@azure/storage-blob";
import axios from "axios";

const AZURE_CONNECTION_STRING = process.env.AZURE_CONNECTION_STRING;
const CONTAINER_NAME = "backup";
const MAX_PAGES = 100; // Limit for safety

export async function getContainerClient() {
    if (!AZURE_CONNECTION_STRING) throw new Error("Missing Azure Connection String");
    const blobServiceClient = BlobServiceClient.fromConnectionString(AZURE_CONNECTION_STRING);
    const containerClient = blobServiceClient.getContainerClient(CONTAINER_NAME);
    await containerClient.createIfNotExists();
    return containerClient;
}

export async function updateStatus(userId: string, status: any) {
    try {
        const container = await getContainerClient();
        const blobName = `${userId}/status.json`;
        const blockBlobClient = container.getBlockBlobClient(blobName);
        await blockBlobClient.upload(JSON.stringify(status), JSON.stringify(status).length, {
            blobHTTPHeaders: { blobContentType: "application/json" }
        });
    } catch (e) {
        console.warn("Failed to update status", e);
    }
}

export async function getStatus(userId: string) {
    try {
        const container = await getContainerClient();
        const blobName = `${userId}/status.json`;
        const blockBlobClient = container.getBlockBlobClient(blobName);

        if (await blockBlobClient.exists()) {
            const downloadBlockBlobResponse = await blockBlobClient.download(0);
            const downloaded = await streamToString(downloadBlockBlobResponse.readableStreamBody);
            return JSON.parse(downloaded);
        }
    } catch (e) {
        return null;
    }
    return null;
}

// Helper to convert stream to string
async function streamToString(readableStream: NodeJS.ReadableStream | undefined): Promise<string> {
    return new Promise((resolve, reject) => {
        const chunks: any[] = [];
        if (!readableStream) return resolve("");
        readableStream.on("data", (data) => {
            chunks.push(data.toString());
        });
        readableStream.on("end", () => {
            resolve(chunks.join(""));
        });
        readableStream.on("error", reject);
    });
}

// Facebook Fetcher
export async function fetchAllData(endpoint: string, token: string) {
    const separator = endpoint.includes("?") ? "&" : "?";
    // Use v18.0 to match login flow
    let url = `https://graph.facebook.com/v18.0/me/${endpoint}${separator}access_token=${token}&limit=100`;
    console.log(`DEBUG: Fetching URL: https://graph.facebook.com/v18.0/me/${endpoint}...`);
    let data: any[] = [];
    let pages = 0;

    while (url && pages < MAX_PAGES) {
        try {
            const res = await axios.get(url, { validateStatus: () => true });
            if (res.status !== 200) {
                console.warn(`Error fetching ${endpoint}:`, JSON.stringify(res.data, null, 2));
                break;
            }
            const json = res.data;
            if (json.data) data.push(...json.data);
            url = json.paging?.next;
            pages++;
        } catch (e) {
            console.error(`Network error fetching ${endpoint}`, e);
            break;
        }
    }
    console.log(`DEBUG: Fetched ${data.length} items for endpoint ${endpoint}`);
    return data;
}

export async function uploadJson(userId: string, folder: string, filename: string, data: any) {
    const container = await getContainerClient();
    const blobName = `${userId}/${folder}/${filename}`;
    const blockBlobClient = container.getBlockBlobClient(blobName);
    const content = JSON.stringify(data, null, 2);
    await blockBlobClient.upload(content, content.length, {
        blobHTTPHeaders: { blobContentType: "application/json" }
    });
}
