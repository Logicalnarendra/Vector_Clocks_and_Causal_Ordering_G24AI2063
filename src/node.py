import json
import threading
import time
from typing import Dict, List, Optional, Tuple
from flask import Flask, request, jsonify
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VectorClock:
    """Vector Clock implementation for causal ordering"""
    
    def __init__(self, node_id: str, num_nodes: int):
        self.node_id = node_id
        self.num_nodes = num_nodes
        # Initialize vector clock with zeros for all nodes
        self.clock = {f"node_{i}": 0 for i in range(num_nodes)}
    
    def increment(self):
        """Increment local clock value"""
        self.clock[self.node_id] += 1
    
    def update(self, received_clock: Dict[str, int]):
        """Update vector clock based on received clock"""
        for node, value in received_clock.items():
            self.clock[node] = max(self.clock[node], value)
        # Increment local clock after update
        self.clock[self.node_id] += 1
    
    def compare(self, other_clock: Dict[str, int]) -> int:
        """
        Compare two vector clocks
        Returns: 1 if self > other, -1 if self < other, 0 if concurrent
        """
        less_than = False
        greater_than = False
        
        for node in self.clock:
            if self.clock[node] < other_clock.get(node, 0):
                less_than = True
            elif self.clock[node] > other_clock.get(node, 0):
                greater_than = True
        
        if greater_than and not less_than:
            return 1
        elif less_than and not greater_than:
            return -1
        else:
            return 0  # Concurrent or equal
    
    def copy(self) -> Dict[str, int]:
        """Return a copy of the current clock"""
        return self.clock.copy()

class KVStoreNode:
    """Distributed Key-Value Store Node with Vector Clocks"""
    
    def __init__(self, node_id: str, port: int, nodes: List[Tuple[str, int]]):
        self.node_id = node_id
        self.port = port
        self.nodes = nodes
        self.num_nodes = len(nodes)
        
        # Initialize vector clock
        self.vector_clock = VectorClock(node_id, self.num_nodes)
        
        # Key-value store
        self.kv_store = {}
        
        # Message buffer for causal delivery
        self.message_buffer = []
        self.buffer_lock = threading.Lock()
        
        # Flask app for HTTP API
        self.app = Flask(__name__)
        self.setup_routes()
        
        # Thread for processing buffered messages
        self.buffer_thread = threading.Thread(target=self._process_buffer, daemon=True)
        self.buffer_thread.start()
    
    def setup_routes(self):
        """Setup Flask routes for the node API"""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({
                'status': 'healthy',
                'node_id': self.node_id,
                'vector_clock': self.vector_clock.clock,
                'kv_store_size': len(self.kv_store)
            })
        
        @self.app.route('/get/<key>', methods=['GET'])
        def get_value(key):
            """Get value for a key"""
            if key in self.kv_store:
                value, clock = self.kv_store[key]
                return jsonify({
                    'key': key,
                    'value': value,
                    'vector_clock': clock,
                    'node_id': self.node_id
                })
            else:
                return jsonify({'error': 'Key not found'}), 404
        
        @self.app.route('/put', methods=['POST'])
        def put_value():
            """Put a key-value pair"""
            data = request.get_json()
            key = data.get('key')
            value = data.get('value')
            
            if key is None or value is None:
                return jsonify({'error': 'Key and value are required'}), 400
            
            # Increment local clock for local write
            self.vector_clock.increment()
            
            # Store with current vector clock
            self.kv_store[key] = (value, self.vector_clock.copy())
            
            logger.info(f"Node {self.node_id}: Local write - key={key}, value={value}, clock={self.vector_clock.clock}")
            
            # Replicate to other nodes
            self._replicate_write(key, value, self.vector_clock.copy())
            
            return jsonify({
                'key': key,
                'value': value,
                'vector_clock': self.vector_clock.clock,
                'node_id': self.node_id
            })
        
        @self.app.route('/replicate', methods=['POST'])
        def replicate():
            """Receive replicated write from another node"""
            data = request.get_json()
            key = data.get('key')
            value = data.get('value')
            sender_clock = data.get('vector_clock')
            sender_id = data.get('sender_id')
            
            logger.info(f"Node {self.node_id}: Received replication - key={key}, value={value}, sender_clock={sender_clock}")
            
            # Check causal delivery
            if self._can_deliver(sender_clock):
                self._apply_replicated_write(key, value, sender_clock, sender_id)
            else:
                # Buffer the message
                with self.buffer_lock:
                    self.message_buffer.append({
                        'key': key,
                        'value': value,
                        'vector_clock': sender_clock,
                        'sender_id': sender_id
                    })
                logger.info(f"Node {self.node_id}: Buffered message from {sender_id}")
            
            return jsonify({'status': 'received'})
        
        @self.app.route('/status', methods=['GET'])
        def status():
            """Get node status including KV store and vector clock"""
            return jsonify({
                'node_id': self.node_id,
                'vector_clock': self.vector_clock.clock,
                'kv_store': self.kv_store,
                'buffer_size': len(self.message_buffer)
            })
    
    def _replicate_write(self, key: str, value: str, clock: Dict[str, int]):
        """Replicate write to other nodes"""
        message = {
            'key': key,
            'value': value,
            'vector_clock': clock,
            'sender_id': self.node_id
        }
        
        for node_host, node_port in self.nodes:
            if f"{node_host}:{node_port}" != f"node_{self.node_id.split('_')[1]}:{self.port}":
                try:
                    response = requests.post(
                        f"http://{node_host}:{node_port}/replicate",
                        json=message,
                        timeout=5
                    )
                    if response.status_code == 200:
                        logger.info(f"Node {self.node_id}: Replicated to {node_host}:{node_port}")
                except Exception as e:
                    logger.error(f"Node {self.node_id}: Failed to replicate to {node_host}:{node_port}: {e}")
    
    def _can_deliver(self, received_clock: Dict[str, int]) -> bool:
        """Check if message can be delivered causally"""
        # Check if all causal dependencies are satisfied
        for node, value in received_clock.items():
            if self.vector_clock.clock.get(node, 0) < value:
                return False
        return True
    
    def _apply_replicated_write(self, key: str, value: str, received_clock: Dict[str, int], sender_id: str):
        """Apply a replicated write"""
        # Update vector clock
        self.vector_clock.update(received_clock)
        
        # Store the value
        self.kv_store[key] = (value, self.vector_clock.copy())
        
        logger.info(f"Node {self.node_id}: Applied replicated write - key={key}, value={value}, clock={self.vector_clock.clock}")
    
    def _process_buffer(self):
        """Process buffered messages in background thread"""
        while True:
            with self.buffer_lock:
                # Check which messages can be delivered
                deliverable = []
                remaining = []
                
                for msg in self.message_buffer:
                    if self._can_deliver(msg['vector_clock']):
                        deliverable.append(msg)
                    else:
                        remaining.append(msg)
                
                # Apply deliverable messages
                for msg in deliverable:
                    self._apply_replicated_write(
                        msg['key'],
                        msg['value'],
                        msg['vector_clock'],
                        msg['sender_id']
                    )
                
                # Update buffer
                self.message_buffer = remaining
            
            time.sleep(0.1)  # Small delay to prevent busy waiting
    
    def run(self):
        """Start the node server"""
        logger.info(f"Starting node {self.node_id} on port {self.port}")
        self.app.run(host='0.0.0.0', port=self.port, debug=False)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 4:
        print("Usage: python node.py <node_id> <port> <nodes_config>")
        print("Example: python node.py node_0 5000 'node_0:5000,node_1:5001,node_2:5002'")
        sys.exit(1)
    
    node_id = sys.argv[1]
    port = int(sys.argv[2])
    nodes_config = sys.argv[3]
    
    # Parse nodes configuration
    nodes = []
    for node_str in nodes_config.split(','):
        host, node_port = node_str.split(':')
        nodes.append((host, int(node_port)))
    
    # Create and run node
    node = KVStoreNode(node_id, port, nodes)
    node.run() 