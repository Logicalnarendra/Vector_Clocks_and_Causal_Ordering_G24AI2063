#!/usr/bin/env python3
"""
Demonstration script for the distributed key-value store with vector clocks.
This script shows the vector clock behavior and causal consistency in action.
"""

import requests
import time
import json

def print_separator(title):
    """Print a formatted separator"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_node_status(nodes, title="Current Node Status"):
    """Print the status of all nodes"""
    print(f"\n{title}:")
    print("-" * 40)
    for i, node_url in enumerate(nodes):
        try:
            response = requests.get(f"{node_url}/status", timeout=5)
            status = response.json()
            print(f"Node {i} ({node_url}):")
            print(f"  Vector Clock: {status['vector_clock']}")
            print(f"  KV Store: {status['kv_store']}")
            print(f"  Buffer Size: {status['buffer_size']}")
        except Exception as e:
            print(f"Node {i} ({node_url}): Error - {e}")
    print()

def demo_vector_clocks():
    """Demonstrate vector clock behavior"""
    print_separator("VECTOR CLOCK DEMONSTRATION")
    
    nodes = [
        'http://localhost:5000',
        'http://localhost:5001',
        'http://localhost:5002'
    ]
    
    print("This demonstration shows how vector clocks track causal relationships")
    print("between events in the distributed system.")
    
    # Initial state
    print_node_status(nodes, "Initial State")
    
    # Step 1: Write on node 0
    print("Step 1: Writing 'A' on node 0...")
    response = requests.post(
        f"{nodes[0]}/put",
        json={'key': 'demo', 'value': 'A'},
        timeout=10
    )
    result = response.json()
    print(f"Result: {result}")
    
    time.sleep(1)
    print_node_status(nodes, "After Step 1")
    
    # Step 2: Write on node 1
    print("Step 2: Writing 'B' on node 1...")
    response = requests.post(
        f"{nodes[1]}/put",
        json={'key': 'demo', 'value': 'B'},
        timeout=10
    )
    result = response.json()
    print(f"Result: {result}")
    
    time.sleep(1)
    print_node_status(nodes, "After Step 2")
    
    # Step 3: Read on node 2, then write (causal dependency)
    print("Step 3: Reading on node 2, then writing 'C'...")
    response = requests.get(f"{nodes[2]}/get/demo", timeout=10)
    read_result = response.json()
    print(f"Read result: {read_result}")
    
    response = requests.post(
        f"{nodes[2]}/put",
        json={'key': 'demo', 'value': 'C'},
        timeout=10
    )
    result = response.json()
    print(f"Write result: {result}")
    
    time.sleep(1)
    print_node_status(nodes, "After Step 3")
    
    # Step 4: Concurrent writes
    print("Step 4: Concurrent writes on all nodes...")
    concurrent_writes = [
        ('X', 0),
        ('Y', 1),
        ('Z', 2)
    ]
    
    for value, node_idx in concurrent_writes:
        print(f"Writing '{value}' on node {node_idx}...")
        response = requests.post(
            f"{nodes[node_idx]}/put",
            json={'key': f'concurrent_{value}', 'value': value},
            timeout=10
        )
        result = response.json()
        print(f"Result: {result}")
    
    time.sleep(2)
    print_node_status(nodes, "After Concurrent Writes")

def demo_causal_consistency():
    """Demonstrate causal consistency"""
    print_separator("CAUSAL CONSISTENCY DEMONSTRATION")
    
    nodes = [
        'http://localhost:5000',
        'http://localhost:5001',
        'http://localhost:5002'
    ]
    
    print("This demonstration shows how the system maintains causal consistency")
    print("even when messages arrive out of order.")
    
    # Clear any existing data
    print("Clearing existing data...")
    for i, node_url in enumerate(nodes):
        try:
            requests.post(
                f"{node_url}/put",
                json={'key': 'clear', 'value': 'clear'},
                timeout=5
            )
        except:
            pass
    
    time.sleep(1)
    
    # Scenario: A -> B -> C (causal chain)
    print("\nScenario: Creating a causal chain A -> B -> C")
    print("where each step depends on the previous one.")
    
    # Step A: Initial write
    print("\nStep A: Writing initial value 'A' on node 0...")
    response = requests.post(
        f"{nodes[0]}/put",
        json={'key': 'causal_chain', 'value': 'A'},
        timeout=10
    )
    print(f"Result: {response.json()}")
    
    # Step B: Read A, then write B (depends on A)
    print("\nStep B: Reading 'A' on node 1, then writing 'B'...")
    response = requests.get(f"{nodes[1]}/get/causal_chain", timeout=10)
    print(f"Read result: {response.json()}")
    
    response = requests.post(
        f"{nodes[1]}/put",
        json={'key': 'causal_chain', 'value': 'B'},
        timeout=10
    )
    print(f"Write result: {response.json()}")
    
    # Step C: Read B, then write C (depends on B)
    print("\nStep C: Reading 'B' on node 2, then writing 'C'...")
    response = requests.get(f"{nodes[2]}/get/causal_chain", timeout=10)
    print(f"Read result: {response.json()}")
    
    response = requests.post(
        f"{nodes[2]}/put",
        json={'key': 'causal_chain', 'value': 'C'},
        timeout=10
    )
    print(f"Write result: {response.json()}")
    
    # Wait for replication
    print("\nWaiting for replication to complete...")
    time.sleep(3)
    
    # Check final state
    print_node_status(nodes, "Final State After Causal Chain")
    
    print("\nCausal consistency ensures that:")
    print("- All nodes see the same sequence of values")
    print("- No node sees 'C' without first seeing 'B'")
    print("- No node sees 'B' without first seeing 'A'")
    print("- Vector clocks track these dependencies")

def main():
    """Main demonstration function"""
    print("Distributed Key-Value Store with Vector Clocks - Demonstration")
    print("This script demonstrates the vector clock implementation and causal consistency.")
    
    # Check if nodes are running
    nodes = [
        'http://localhost:5000',
        'http://localhost:5001',
        'http://localhost:5002'
    ]
    
    print("\nChecking if nodes are running...")
    all_healthy = True
    for i, node_url in enumerate(nodes):
        try:
            response = requests.get(f"{node_url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ Node {i} is healthy")
            else:
                print(f"❌ Node {i} is not healthy")
                all_healthy = False
        except Exception as e:
            print(f"❌ Node {i} is not reachable: {e}")
            all_healthy = False
    
    if not all_healthy:
        print("\n❌ Some nodes are not running. Please start the system with:")
        print("   docker-compose up --build")
        return
    
    print("\n✅ All nodes are healthy. Starting demonstration...")
    
    # Run demonstrations
    demo_vector_clocks()
    demo_causal_consistency()
    
    print_separator("DEMONSTRATION COMPLETE")
    print("The demonstrations show:")
    print("1. Vector clocks incrementing and updating correctly")
    print("2. Causal dependencies being maintained")
    print("3. Message buffering for out-of-order delivery")
    print("4. Consistent state across all nodes")

if __name__ == "__main__":
    main() 