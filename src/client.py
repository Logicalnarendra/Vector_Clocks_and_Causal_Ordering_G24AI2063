import requests
import time
import json
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KVStoreClient:
    """Client for interacting with the distributed key-value store"""
    
    def __init__(self, nodes: List[str]):
        """
        Initialize client with list of node URLs
        nodes: List of node URLs (e.g., ['http://node_0:5000', 'http://node_1:5001', 'http://node_2:5002'])
        """
        self.nodes = nodes
        self.current_node = 0  # Round-robin node selection
    
    def _get_next_node(self) -> str:
        """Get next node for round-robin load balancing"""
        node = self.nodes[self.current_node]
        self.current_node = (self.current_node + 1) % len(self.nodes)
        return node
    
    def put(self, key: str, value: str, node_index: int = None) -> Dict[str, Any]:
        """Put a key-value pair"""
        if node_index is not None:
            node_url = self.nodes[node_index]
        else:
            node_url = self._get_next_node()
        
        try:
            response = requests.post(
                f"{node_url}/put",
                json={'key': key, 'value': value},
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"PUT {key}={value} on {node_url} -> {result}")
            return result
        except Exception as e:
            logger.error(f"PUT failed on {node_url}: {e}")
            raise
    
    def get(self, key: str, node_index: int = None) -> Dict[str, Any]:
        """Get a value for a key"""
        if node_index is not None:
            node_url = self.nodes[node_index]
        else:
            node_url = self._get_next_node()
        
        try:
            response = requests.get(f"{node_url}/get/{key}", timeout=10)
            if response.status_code == 404:
                logger.info(f"GET {key} on {node_url} -> Key not found")
                return {'error': 'Key not found'}
            
            response.raise_for_status()
            result = response.json()
            logger.info(f"GET {key} on {node_url} -> {result}")
            return result
        except Exception as e:
            logger.error(f"GET failed on {node_url}: {e}")
            raise
    
    def get_status(self, node_index: int = None) -> Dict[str, Any]:
        """Get node status"""
        if node_index is not None:
            node_url = self.nodes[node_index]
        else:
            node_url = self._get_next_node()
        
        try:
            response = requests.get(f"{node_url}/status", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Status request failed on {node_url}: {e}")
            raise
    
    def wait_for_health(self, timeout: int = 30) -> bool:
        """Wait for all nodes to be healthy"""
        logger.info("Waiting for all nodes to be healthy...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            all_healthy = True
            for i, node_url in enumerate(self.nodes):
                try:
                    response = requests.get(f"{node_url}/health", timeout=5)
                    if response.status_code != 200:
                        all_healthy = False
                        logger.info(f"Node {i} not ready yet...")
                        break
                except:
                    all_healthy = False
                    logger.info(f"Node {i} not ready yet...")
                    break
            
            if all_healthy:
                logger.info("All nodes are healthy!")
                return True
            
            time.sleep(1)
        
        logger.error("Timeout waiting for nodes to be healthy")
        return False

def test_causal_consistency():
    """Test causal consistency with a specific scenario"""
    logger.info("=== Testing Causal Consistency with Vector Clocks ===")
    
    # Initialize client
    client = KVStoreClient([
        'http://node_0:5000',
        'http://node_1:5001', 
        'http://node_2:5002'
    ])
    
    # Wait for all nodes to be ready
    if not client.wait_for_health():
        logger.error("Nodes not ready, exiting test")
        return
    
    logger.info("\n=== Scenario: Causal Dependencies Test ===")
    logger.info("This test demonstrates that causal consistency is maintained")
    logger.info("even when messages arrive out of order.")
    
    # Step 1: Write initial value on node 0
    logger.info("\n1. Writing initial value 'hello' on node 0...")
    result1 = client.put("message", "hello", node_index=0)
    logger.info(f"   Result: {result1}")
    
    # Step 2: Read the value on node 1 (creates causal dependency)
    logger.info("\n2. Reading value on node 1 (creates causal dependency)...")
    result2 = client.get("message", node_index=1)
    logger.info(f"   Result: {result2}")
    
    # Step 3: Update the value on node 1 (causally depends on step 2)
    logger.info("\n3. Updating value to 'hello world' on node 1...")
    result3 = client.put("message", "hello world", node_index=1)
    logger.info(f"   Result: {result3}")
    
    # Step 4: Write a concurrent update on node 2 (no causal dependency)
    logger.info("\n4. Writing concurrent update 'goodbye' on node 2...")
    result4 = client.put("message", "goodbye", node_index=2)
    logger.info(f"   Result: {result4}")
    
    # Step 5: Wait a bit for replication
    logger.info("\n5. Waiting for replication to complete...")
    time.sleep(3)
    
    # Step 6: Check final state on all nodes
    logger.info("\n6. Checking final state on all nodes...")
    for i in range(3):
        status = client.get_status(node_index=i)
        logger.info(f"   Node {i} status:")
        logger.info(f"     Vector Clock: {status['vector_clock']}")
        logger.info(f"     KV Store: {status['kv_store']}")
        logger.info(f"     Buffer Size: {status['buffer_size']}")
    
    # Step 7: Read from all nodes to verify consistency
    logger.info("\n7. Reading from all nodes to verify consistency...")
    for i in range(3):
        result = client.get("message", node_index=i)
        logger.info(f"   Node {i}: {result}")
    
    logger.info("\n=== Test Complete ===")
    logger.info("The system should maintain causal consistency:")
    logger.info("- If a node reads a value and then updates it, all nodes")
    logger.info("  must see the read value before seeing the update.")
    logger.info("- Concurrent updates may be resolved differently on different nodes")
    logger.info("- Vector clocks ensure proper causal ordering")

def test_out_of_order_delivery():
    """Test that out-of-order message delivery is handled correctly"""
    logger.info("\n=== Testing Out-of-Order Message Delivery ===")
    
    client = KVStoreClient([
        'http://node_0:5000',
        'http://node_1:5001', 
        'http://node_2:5002'
    ])
    
    if not client.wait_for_health():
        return
    
    logger.info("This test simulates network delays that cause messages to arrive out of order.")
    
    # Step 1: Write on node 0
    logger.info("\n1. Writing 'step1' on node 0...")
    client.put("test_key", "step1", node_index=0)
    
    # Step 2: Write on node 1 (depends on step 1)
    logger.info("\n2. Writing 'step2' on node 1...")
    client.put("test_key", "step2", node_index=1)
    
    # Step 3: Write on node 0 again (depends on step 2)
    logger.info("\n3. Writing 'step3' on node 0...")
    client.put("test_key", "step3", node_index=0)
    
    # Step 4: Check buffer states
    logger.info("\n4. Checking message buffers...")
    time.sleep(2)
    for i in range(3):
        status = client.get_status(node_index=i)
        logger.info(f"   Node {i} buffer size: {status['buffer_size']}")
    
    # Step 5: Final state
    logger.info("\n5. Final state after processing...")
    time.sleep(3)
    for i in range(3):
        result = client.get("test_key", node_index=i)
        logger.info(f"   Node {i}: {result}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "causal":
        test_causal_consistency()
    elif len(sys.argv) > 1 and sys.argv[1] == "order":
        test_out_of_order_delivery()
    else:
        print("Usage: python client.py [causal|order]")
        print("  causal: Test causal consistency")
        print("  order:  Test out-of-order message delivery")
        print("\nRunning both tests...")
        test_causal_consistency()
        test_out_of_order_delivery() 