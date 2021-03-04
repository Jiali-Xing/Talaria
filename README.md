# Talaria

Talaria is a novel permissioned blockchain simulator based on open source blockchain simulator [BlockSim](https://github.com/carlosfaria94/blocksim). We significantly extend the capability of BlockSim, to support permissioned blockchains. To the best of our knowledge, Talaria is the first blockchain simulator designed for simulating private blockchain models. 

Presently, a simplified version of Proof-of-Authority and the complete pBFT consensus protocols are implemented. Other permissioned protocols such as PoET can easily be included into our flexible modeling framework. Moreover, our new blockchain simulator handles  different types of faulty authorities and a variable number of transactions generated per day at every node. These features make our Talaria ideal for testing and simulating protocols for a range of use cases including the challenging setting of supply chain management. We also demonstrate its application on a supply chain management example that utilizes the practical Byzantine Fault Tolerance (pBFT) protocol. 

Protocols Out-of-box:
 - Simplified PoA
 - pBFT
 - PoET

Other features are also included for convenience:
 - Simulating for certain time duration v.s. until finish certain amount of transactions.
 - Counting inter-regional transactions.
 - Multiple (days') simulation using the same chain.
 - Switching output on and off
 
---

## Overview
There are several important classes that are needed by the simulator. There is needed a main file, a transaction factory, and a node factory, as well as a variety of configuration and parameter files. Each is described below in detail.

## main.py
This function takes in a json file with the number of transactions for each node on each day, and uses imported per protocol transaction and node factories, as well as per protocol network files to create the simulation world. This function also relies on the following files: config.json, latency.json, throughput_received.json, throughput_sent.json, delays.json. This function will also call the network's start_heartbeat, and run the simulation using the world's start_simulation function.

## config.json
This file includes parameters such as the number of transactions per block, block size limit, and the max size of each block.

## latency.json
This file includes the latency distributions from each location to each other location. There are some researches in literature which can help find these distributions for a specific use case (TODO: insert link to relevant resources/papers here)

## throughput_received.json
For each location, this file includes outgoing throughput distributions and parameters to every other location.

## throughput_sent.json
For each location, this file includes incoming throughput distributions and parameters to every other location.

## delays.json
This file includes distribution specifications for a variety of other delays that may occur. For example, the distributions for the transaction validation time, the block validation time, and the time between blocks. 

## Transaction Factory

## Node Factory

## Network

---
# Run the Simulation
Here is how you can run this simulation
## Installation 
First, clone this repo to your local directory. 
Then, install the dependences, I suggest that you use conda:
```
conda env create -f talaria.yml
```

## Running 
```
cd ./talaria

conda activate talaria
export PYTHONPATH='.'

python ./blocksim/pbft_main.py
```
This runs the pBFT protocol as default.

---
# Acknowledgment

This material is based on work supported by the Defense Advanced Research Projects Agency (DARPA) and Space and Naval Warfare Systems Center, Pacific (SSC Pacific) under contract number N6600118C4031.

