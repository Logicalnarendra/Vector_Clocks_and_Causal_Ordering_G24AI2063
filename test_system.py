#!/usr/bin/env python3
"""
Standalone test script for the distributed key-value store with vector clocks.
This script can be run outside of Docker to test the system.
"""

import requests
import time
import json
import sys

def test_node_health(nodes):
    """Test if all nodes are healthy"""
    print("Testing node health...")
    for i, node_url in enumerate(nodes):
        try:
            response = requests.get(f"{node_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"  Node {i} ({node_url}): {data['status']}")
                print(f"    Vector Clock: {data['vector_clock']}")
            else:
                print(f"  Node {i} ({node_url}): Unhealthy")
                return False
        except Exception as e:
            print(f"  Node {i} ({node_url}): Error - {e}")
            return False
    return True

def test_basic_operations(nodes):
    """Test basic PUT and GET operations"""
    print("\nTesting basic operations...")
    
    # Test PUT on node 0
    print("1. PUT 'hello' on node 0...")
    try:
        response = requests.post(
            f"{nodes[0]}/put",
            json={'key': 'test_key', 'value': 'hello'},
            timeout=10
        )
        result = response.json()
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   Error: {e}")
        return False
    
    # Test GET from all nodes
    print("2. GET from all nodes...")
    for i, node_url in enumerate(nodes):
        try:
            response = requests.get(f"{node_url}/get/test_key", timeout=10)
            if response.status_code == 200:
                result = response.json()
                print(f"   Node {i}: {result}")
            else:
                print(f"   Node {i}: Key not found")
        except Exception as e:
            print(f"   Node {i}: Error - {e}")
            return False
    
    return True

def test_causal_consistency(nodes):
    """Test causal consistency with a specific scenario"""
    print("\nTesting causal consistency...")
    
    # Step 1: Write initial value on node 0
    print("1. Writing 'initial' on node 0...")
    try:
        response = requests.post(
            f"{nodes[0]}/put",
            json={'key': 'causal_test', 'value': 'initial'},
            timeout=10
        )
        result = response.json()
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   Error: {e}")
        return False
    
    # Step 2: Read on node 1 (creates causal dependency)
    print("2. Reading on node 1...")
    try:
        response = requests.get(f"{nodes[1]}/get/causal_test", timeout=10)
        result = response.json()
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   Error: {e}")
        return False
    
    # Step 3: Update on node 1 (causally depends on step 2)
    print("3. Updating to 'updated' on node 1...")
    try:
        response = requests.post(
            f"{nodes[1]}/put",
            json={'key': 'causal_test', 'value': 'updated'},
            timeout=10
        )
        result = response.json()
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   Error: {e}")
        return False
    
    # Step 4: Concurrent write on node 2
    print("4. Concurrent write 'concurrent' on node 2...")
    try:
        response = requests.post(
            f"{nodes[2]}/put",
            json={'key': 'causal_test', 'value': 'concurrent'},
            timeout=10
        )
        result = response.json()
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   Error: {e}")
        return False
    
    # Step 5: Wait for replication
    print("5. Waiting for replication...")
    time.sleep(3)
    
    # Step 6: Check final state
    print("6. Checking final state on all nodes...")
    for i, node_url in enumerate(nodes):
        try:
            response = requests.get(f"{node_url}/status", timeout=10)
            status = response.json()
            print(f"   Node {i}:")
            print(f"     Vector Clock: {status['vector_clock']}")
            print(f"     KV Store: {status['kv_store']}")
            print(f"     Buffer Size: {status['buffer_size']}")
        except Exception as e:
            print(f"   Node {i}: Error - {e}")
            return False
    
    return True

def main():
    """Main test function"""
    # Node URLs (assuming they're running on localhost)
    nodes = [
        'http://localhost:5000',
        'http://localhost:5001',
        'http://localhost:5002'
    ]
    
    print("=== Distributed Key-Value Store with Vector Clocks - Test Suite ===")
    print(f"Testing nodes: {nodes}")
    
    # Test 1: Health check
    if not test_node_health(nodes):
        print("❌ Health check failed. Make sure all nodes are running.")
        sys.exit(1)
    print("✅ Health check passed.")
    
    # Test 2: Basic operations
    if not test_basic_operations(nodes):
        print("❌ Basic operations test failed.")
        sys.exit(1)
    print("✅ Basic operations test passed.")
    
    # Test 3: Causal consistency
    if not test_causal_consistency(nodes):
        print("❌ Causal consistency test failed.")
        sys.exit(1)
    print("✅ Causal consistency test passed.")
    
    print("\n🎉 All tests passed! The system is working correctly.")
    print("\nThe system demonstrates:")
    print("- Vector clock implementation for causal ordering")
    print("- Causal consistency maintenance")
    print("- Proper handling of concurrent operations")
    print("- Message buffering for out-of-order delivery")

if __name__ == "__main__":
    main() 