# Reliable UDP (RUDP) Protocol

This project implements a custom reliable transport-layer protocol on top of UDP. The goal is to explore protocol modeling and reliability mechanisms typically found in TCP, while maintaining explicit control over packet handling, retransmissions, and acknowledgments.

The implementation focuses on correctness, clarity, and protocol behavior under loss, delay, and out-of-order delivery, rather than on throughput optimization.

## Overview

RUDP provides reliable, ordered, bidirectional data transfer over an unreliable UDP channel. It introduces sequence numbers, acknowledgments, retransmissions, and connection termination semantics to compensate for UDP’s lack of delivery guarantees.

The protocol supports full-duplex communication, allowing both sender and receiver to transmit data and acknowledgments, including piggybacked ACKs where appropriate.

## Key Features

- Reliable data transfer over UDP
- Sliding window–based flow control
- Sequence numbers and cumulative acknowledgments
- Out-of-order packet buffering with in-order delivery
- Retransmission on timeout with TTL-based packet expiry
- Piggybacked acknowledgments to reduce control overhead
- Graceful connection termination using FIN and FIN+ACK flags
- CRC32-based checksum for packet integrity verification

## Design Notes

Packets are explicitly serialized and deserialized, with all protocol fields manually defined and validated. Packet corruption, loss, duplication, and reordering are handled at the protocol level.

The receiver acknowledges the next expected sequence number even when packets arrive out of order, ensuring progress while buffering future packets. Retransmissions decrement packet TTL to prevent infinite resend loops.

The protocol is intentionally TCP-like and serves as a foundation for experimenting with alternative designs focused on low latency, such as VoIP or real-time game networking protocols.

## Project Structure

The project consists of four core modules:
- Packet construction and validation
- UDP socket abstractions
- Sender-side protocol logic
- Receiver-side protocol logic

Each component is kept separate to clearly reflect protocol responsibilities.

## Usage

Run the receiver first, followed by the sender, in separate terminals. Both communicate over UDP sockets on localhost. No external dependencies are required.

## Requirements

- Python 3.x
- Standard Python libraries only (socket, struct, zlib, time)

## Scope

This project is an academic mini-project intended to demonstrate understanding of transport-layer protocol design. It is not intended for production use but provides a solid base for further experimentation with high-performance or low-latency protocols.
