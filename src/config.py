"""Central config: env vars, network settings, HH Goa theme tokens."""
import os

from dotenv import load_dotenv

load_dotenv()

# --- SerpApi ---
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")

# --- Polygon Amoy testnet ---
AMOY_RPC_URL = os.getenv("AMOY_RPC_URL", "https://polygon-amoy-bor-rpc.publicnode.com")
AMOY_CHAIN_ID = 80002
WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY", "")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS", "")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "")
POLYGONSCAN_TX_URL = "https://amoy.polygonscan.com/tx/{tx_hash}"

# --- Pinata (IPFS) ---
PINATA_API_KEY = os.getenv("PINATA_API_KEY", "")
PINATA_API_SECRET = os.getenv("PINATA_API_SECRET", "")
PINATA_JWT = os.getenv("PINATA_JWT", "")

# --- Face match verification ---
FACE_MATCH_DISTANCE_THRESHOLD = 0.68  # ArcFace cosine distance; lower = stricter

# --- HH Goa theme tokens ---
THEME = {
    "bg": "#0B1220",
    "accent_teal": "#14B8A6",
    "accent_gold": "#F59E0B",
    "text": "#F5F0E6",
}
