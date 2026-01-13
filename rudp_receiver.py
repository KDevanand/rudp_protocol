from packet import serialize_packet

from rudp_socket import send_packet, recv_packet

import socket

import time

WINDOW_SIZE = 3

RECEIVER_MESSAGES = [

"Receiver packet 1",

"Receiver packet 2",

"Receiver packet 3"

]

CONN_ID = 12345

MAX_RETRIES = 5

MIN_RTO = 0.05

MAX_RTO = 1.0

FIN_TIMEOUT = 1.0

MAX_FIN_RETRIES = 3

TOTAL_EXPECTED_PACKETS = 5

MAX_TIMEOUTS = 100

def estimate_rto(rtt_samples):

if not rtt_samples:

    return 0.2

srtt = sum(rtt_samples) / len(rtt_samples)

return max(MIN_RTO, min(MAX_RTO, srtt * 1.5))

def main(debug=False):

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

sock.bind(("localhost", 54321))

sock.settimeout(0.2)



received_packets = {}

next_expected_seq = 1

sent_packets = {}

acked_packets = [False] * len(RECEIVER_MESSAGES)

receiver_base = 1

receiver_seq = 1

rtt_samples = []

state = "OPEN"

sender_addr = None

timeout_count = 0



if debug:

    print("[RECEIVER] Waiting for packets...")



while state != "CLOSED":

    if sender_addr and state == "OPEN":

        while receiver_seq < receiver_base + WINDOW_SIZE and receiver_seq <= len(RECEIVER_MESSAGES):

            payload = RECEIVER_MESSAGES[receiver_seq - 1].encode()

            packet = serialize_packet(CONN_ID, receiver_seq, 0, payload, 0, 255)

            if debug:

                print(f"[RECEIVER] Preparing packet seq={receiver_seq}, size={len(packet)} bytes")

            send_packet(sock, sender_addr, packet, debug=debug)

            sent_packets[receiver_seq] = (packet, time.time(), 0)

            if debug:

                print(f"[RECEIVER] Sent Packet {receiver_seq} to {sender_addr}")

            receiver_seq += 1



    try:

        header, payload, addr = recv_packet(sock, debug=debug)

        timeout_count = 0 



        if header["Conn ID"] != CONN_ID:

            if debug:

                print(f"[RECEIVER] Dropped packet with wrong Conn ID: {header['Conn ID']}")

            continue



        if sender_addr is None:

            sender_addr = addr

            if debug:

                print(f"[RECEIVER] Set sender address to {sender_addr}")



        seq_no = header["Seq No"]

        ack_no = header["Ack No"]

        flags = header["Flags"]



        if ack_no > 0 and ack_no <= len(acked_packets):

            for i in range(receiver_base, ack_no + 1):

                if not acked_packets[i - 1]:

                    acked_packets[i - 1] = True

                    if i in sent_packets:

                        send_time = sent_packets[i][1]

                        rtt_samples.append(time.time() - send_time)

                        if debug:

                            print(f"[RECEIVER] Received ACK {i}, RTT={rtt_samples[-1]:.3f}s")

                        del sent_packets[i]

            while receiver_base <= len(acked_packets) and acked_packets[receiver_base - 1]:

                receiver_base += 1

            if receiver_base > len(RECEIVER_MESSAGES) and state == "OPEN":

                if debug:

                    print("[RECEIVER] All packets ACKed")



        if flags in (0, 1) and payload and seq_no > 0:

            if seq_no not in received_packets and seq_no <= TOTAL_EXPECTED_PACKETS:

                received_packets[seq_no] = payload.decode()

                if debug:

                    print(f"[RECEIVER] Received Packet {seq_no}: {payload.decode()}")

            else:

                if debug:

                    print(f"[RECEIVER] Duplicate Packet {seq_no}")

            

            out_payload = b""

            out_seq = 0

            if receiver_seq <= len(RECEIVER_MESSAGES) and receiver_seq < receiver_base + WINDOW_SIZE and sender_addr:

                out_payload = RECEIVER_MESSAGES[receiver_seq - 1].encode()

                out_seq = receiver_seq

            

            flags_to_send = 0 if out_payload else 1

            packet = serialize_packet(CONN_ID, out_seq, seq_no, out_payload, flags_to_send, 255)

            send_packet(sock, addr, packet, debug=debug)

            

            if out_payload:

                sent_packets[receiver_seq] = (packet, time.time(), 0)

                if debug:

                    print(f"[RECEIVER] Sent piggybacked ACK {seq_no} + Data {receiver_seq} to {addr}")

                receiver_seq += 1

            else:

                if debug:

                    print(f"[RECEIVER] Sent ACK {seq_no} to {addr}")



            while next_expected_seq in received_packets:

                if debug:

                    print(f"[RECEIVER] Delivered Packet {next_expected_seq}")

                next_expected_seq += 1

                if next_expected_seq > TOTAL_EXPECTED_PACKETS and state == "OPEN":

                    state = "CLOSING"

                    if debug:

                        print("[RECEIVER] All expected packets received, moving to CLOSING")



        if flags == 4 and state in ("OPEN", "CLOSING"):

            if debug:

                print(f"[RECEIVER] Received FIN, sending FIN+ACK")

            state = "CLOSING"

            fin_ack = serialize_packet(CONN_ID, 0, 0, b"", 5, 255)

            send_packet(sock, addr, fin_ack, debug=debug)

            state = "CLOSED" 



    except socket.timeout:

        timeout_count += 1

        if timeout_count >= MAX_TIMEOUTS:

            if debug:

                print(f"[RECEIVER] No packets received after {MAX_TIMEOUTS * 0.2:.1f}s, closing")

            state = "CLOSED"

            continue

        if state == "OPEN" and sender_addr:

            current_time = time.time()

            rto = estimate_rto(rtt_samples)

            for seq in list(sent_packets.keys()):

                packet, send_time, retries = sent_packets[seq]

                if current_time - send_time >= rto:

                    if retries >= MAX_RETRIES:

                        if debug:

                            print(f"[RECEIVER] Packet {seq} dropped after {retries} retries")

                        acked_packets[seq - 1] = True

                        del sent_packets[seq]

                        while receiver_base <= len(acked_packets) and acked_packets[receiver_base - 1]:

                            receiver_base += 1

                        continue

                    packet = serialize_packet(CONN_ID, seq, 0, 

                                             RECEIVER_MESSAGES[seq - 1].encode(), 0, 255)

                    send_packet(sock, sender_addr, packet, debug=debug)

                    sent_packets[seq] = (packet, time.time(), retries + 1)

                    if debug:

                        print(f"[RECEIVER] Timeout, resent Packet {seq}, retries={retries + 1}")

        elif state == "CLOSING" and sender_addr:

            if "fin_retries" not in locals():

                fin_retries = 0

                fin_sent_time = 0

            if time.time() - fin_sent_time >= FIN_TIMEOUT:

                if fin_retries >= MAX_FIN_RETRIES:

                    if debug:

                        print("[RECEIVER] Max FIN+ACK retries reached, moving to CLOSED")

                    state = "CLOSED"

                    continue

                fin_ack = serialize_packet(CONN_ID, 0, 0, b"", 5, 255)

                send_packet(sock, sender_addr, fin_ack, debug=debug)

                if debug:

                    print(f"[RECEIVER] Sent FIN+ACK, attempt {fin_retries + 1}")

                fin_retries += 1

                fin_sent_time = time.time()

    except OSError as e:

        if state == "CLOSING":

            if debug:

                print(f"[RECEIVER] Connection closed by sender, moving to CLOSED")

            state = "CLOSED"

            continue

        if debug:

            print(f"[RECEIVER] Receive error: {e}")

        continue

    except ValueError as e:

        if debug:

            print(f"[RECEIVER] Invalid packet: {e}")

        continue



sock.close()

if debug:

    print("[RECEIVER] Closed")

if name == "main":

main(debug=True)
