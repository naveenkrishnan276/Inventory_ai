"""
Real-time retail sales event simulator for a grocery company.
Runs a TCP *server* on localhost:9999, accepts client connections
(e.g. PySpark Structured Streaming), and pushes newline-delimited
JSON events to every connected client.
"""

import json
import socket
import random
import threading
import time
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HOST = "localhost"
PORT = 9999

STORE_IDS = [f"STORE_{i:03d}" for i in range(1, 6)]
PRODUCT_IDS = [f"PROD_{i:03d}" for i in range(1, 51)]
PAYMENT_MODES = ["UPI", "Card", "Cash"]

# Category mapping: product ranges -> category name
CATEGORY_MAP = {
    range(1, 11): "Rice",
    range(11, 21): "Snacks",
    range(21, 31): "Beverages",
    range(31, 41): "Dairy",
    range(41, 51): "Personal Care",
}

# Realistic base-price ranges per category (INR)
PRICE_RANGE = {
    "Rice":          (45.0, 120.0),
    "Snacks":        (10.0, 60.0),
    "Beverages":     (15.0, 80.0),
    "Dairy":         (25.0, 90.0),
    "Personal Care": (30.0, 150.0),
}

ANOMALY_PROBABILITY = 0.05  # 5 % chance per event

# Thread-safe set of connected clients
clients: list[socket.socket] = []
clients_lock = threading.Lock()


def get_category(product_id: str) -> str:
    """Map a product ID to its category."""
    num = int(product_id.split("_")[1])
    for rng, cat in CATEGORY_MAP.items():
        if num in rng:
            return cat
    return "General"


def generate_event() -> dict:
    """Create a single sales event, with occasional anomalies."""
    product_id = random.choice(PRODUCT_IDS)
    category = get_category(product_id)
    low, high = PRICE_RANGE.get(category, (10.0, 100.0))

    is_anomaly = random.random() < ANOMALY_PROBABILITY

    if is_anomaly:
        # Anomaly: price spike (2×-5×) and/or unusually high quantity
        unit_price = round(random.uniform(high * 2, high * 5), 2)
        quantity = random.randint(10, 50)
    else:
        unit_price = round(random.uniform(low, high), 2)
        quantity = random.randint(1, 5)

    return {
        "event_time": datetime.now(timezone.utc).isoformat(),
        "store_id": random.choice(STORE_IDS),
        "product_id": product_id,
        "category": category,
        "unit_price": unit_price,
        "quantity": quantity,
        "payment_mode": random.choice(PAYMENT_MODES),
        "is_anomaly": is_anomaly,
    }


def accept_clients(server_sock: socket.socket):
    """Background thread: accept new client connections."""
    while True:
        try:
            conn, addr = server_sock.accept()
            with clients_lock:
                clients.append(conn)
            print(f"Client connected: {addr}  (total: {len(clients)})")
        except OSError:
            break


def broadcast(payload: bytes):
    """Send payload to every connected client; remove dead ones."""
    dead = []
    with clients_lock:
        for c in clients:
            try:
                c.sendall(payload)
            except (BrokenPipeError, ConnectionResetError, OSError):
                dead.append(c)
        for c in dead:
            clients.remove(c)
            c.close()
    if dead:
        print(f"Removed {len(dead)} disconnected client(s).")


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"Sales stream server listening on {HOST}:{PORT}")
    print("Waiting for clients (e.g. PySpark) to connect …\n")

    # Accept clients in a background thread
    acceptor = threading.Thread(target=accept_clients, args=(server,), daemon=True)
    acceptor.start()

    try:
        while True:
            event = generate_event()
            payload = (json.dumps(event) + "\n").encode("utf-8")

            tag = " ** ANOMALY **" if event["is_anomaly"] else ""
            print(f"[{event['event_time']}] {event['store_id']} | "
                  f"{event['product_id']} ({event['category']}) | "
                  f"₹{event['unit_price']} × {event['quantity']} | "
                  f"{event['payment_mode']}{tag}")

            broadcast(payload)
            time.sleep(random.uniform(1, 2))

    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        server.close()
        with clients_lock:
            for c in clients:
                c.close()


if __name__ == "__main__":
    main()
