# Distributed Key-Value Store with Vector Clocks

This project implements a causally consistent distributed key-value store using Vector Clocks to ensure proper ordering of events in a distributed system.

## Architecture

The system consists of:
- **3 Node Services**: Each running a Python Flask application with vector clock logic
- **Client Service**: For testing and demonstrating causal consistency
- **Docker Network**: Enabling communication between all services

## Key Features

1. **Vector Clock Implementation**: Each node maintains a vector clock to track causal relationships
2. **Causal Consistency**: Ensures that causally related events are processed in the correct order
3. **Message Buffering**: Out-of-order messages are buffered until causal dependencies are satisfied
4. **HTTP API**: RESTful interface for key-value operations
5. **Containerized**: Fully containerized using Docker and Docker Compose

## Vector Clock Rules

1. **Local Event**: Increment local clock value
2. **Send Message**: Include current vector clock with the message
3. **Receive Message**: Update local clock by taking max of each component, then increment local clock
4. **Causal Delivery**: Only deliver message when all causal dependencies are satisfied

## API Endpoints

Each node exposes the following endpoints:

- `GET /health` - Health check
- `GET /get/<key>` - Retrieve a value
- `POST /put` - Store a key-value pair
- `POST /replicate` - Internal endpoint for replication
- `GET /status` - Get node status (vector clock, KV store, buffer)

## Building and Running

### Prerequisites

- Docker
- Docker Compose

### Quick Start

1. **Clone and navigate to the project directory**:
   ```bash
   cd vector-clock-kv-store
   ```

2. **Build and start the system**:
   ```bash
   docker-compose up --build
   ```

3. **The system will automatically run tests** to demonstrate causal consistency.

### Manual Testing

To run tests manually after the system is up:

```bash
# Test causal consistency
docker exec kv_client python src/client.py causal

# Test out-of-order delivery
docker exec kv_client python src/client.py order

# Run both tests
docker exec kv_client python src/client.py
```

### Individual Node Access

You can interact with individual nodes directly:

```bash
# Check node 0 status
curl http://localhost:5000/status

# Put a key-value pair on node 0
curl -X POST http://localhost:5000/put \
  -H "Content-Type: application/json" \
  -d '{"key": "test", "value": "hello"}'

# Get a value from node 1
curl http://localhost:5001/get/test
```

## Causal Consistency Test Scenario

The system includes a comprehensive test that demonstrates causal consistency:

1. **Write on Node 0**: Initial value "hello"
2. **Read on Node 1**: Creates causal dependency
3. **Update on Node 1**: Changes to "hello world" (causally depends on step 2)
4. **Concurrent Write on Node 2**: Writes "goodbye" (no causal dependency)
5. **Verification**: All nodes maintain causal consistency

## Understanding the Logs

The logs show:
- Vector clock values for each operation
- Message buffering when causal dependencies aren't met
- Replication between nodes
- Final state consistency

## Stopping the System

```bash
docker-compose down
```

## Project Structure

```
vector-clock-kv-store/
├── src/
│   ├── node.py          # Node implementation with vector clocks
│   └── client.py        # Client for testing
├── Dockerfile           # Container configuration
├── docker-compose.yml   # Orchestration
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Technical Details

### Vector Clock Implementation

The `VectorClock` class implements:
- Clock initialization for all nodes
- Local event increment
- Clock update on message receipt
- Clock comparison for causal ordering

### Causal Delivery

The system ensures causal delivery by:
1. Checking if all causal dependencies are satisfied
2. Buffering messages that arrive out of order
3. Processing buffered messages in a background thread
4. Applying vector clock rules for each operation

### Network Communication

Nodes communicate via HTTP REST APIs:
- Synchronous replication for writes
- Health checks for system monitoring
- Status endpoints for debugging

## Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 5000, 5001, 5002 are available
2. **Network issues**: Check Docker network connectivity
3. **Container startup**: Verify all containers are running with `docker-compose ps`

### Debugging

1. **Check container logs**:
   ```bash
   docker-compose logs node_0
   docker-compose logs node_1
   docker-compose logs node_2
   ```

2. **Access container shell**:
   ```bash
   docker exec -it kv_node_0 bash
   ```

3. **Check network connectivity**:
   ```bash
   docker network ls
   docker network inspect vector-clock-kv-store_kv_network
   ``` 