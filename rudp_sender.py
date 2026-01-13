from packet import serialize_packet

from rudp_socket import send_packet, recv_packet

import socket

import time

WINDOW_SIZE = 3

SENDER_MESSAGES = [

"Data Packet 1",

"Data Packet 2",

"Data Packet 3",

"Data Packet 4",

"Data Packet 5"

]

CONN_ID = 12345

MAX_RETRIES = 5

MIN_RTO = 0.05

MAX_RTO = 1.0

FIN_TIMEOUT = 1.0

MAX_FIN_RETRIES = 3

MAX_TIMEOUTS = 100

def estimate_rto(rtt_samples):

if not rtt_samples:

    return 0.2

srtt = sum(rtt_samples) / len(rtt_samples)

return max(MIN_RTO, min(MAX_RTO, srtt * 1.5))

def main(debug=False):

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

sock.bind(("localhost", 54322))

sock.settimeout(0.2)

receiver_addr = ("localhost", 54321)



sent_packets = {}

acked_packets = [False] * len(SENDER_MESSAGES)

base = 1

next_seq = 1

rtt_samples = []

state = "OPEN"

receiver_packets = {}

next_expected_receiver_seq = 1

timeout_count = 0



if debug:

    print("[SENDER] Starting...")



while state != "CLOSED":

    while state == "OPEN" and next_seq < base + WINDOW_SIZE and next_seq <= len(SENDER_MESSAGES):

        payload = SENDER_MESSAGES[next_seq - 1].encode()

        packet = serialize_packet(CONN_ID, next_seq, 0, payload, 0, 255)

        if debug:

            print(f"[SENDER] Preparing packet seq={next_seq}, size={len(packet)} bytes")

        send_packet(sock, receiver_addr, packet, debug=debug)

        sent_packets[next_seq] = (packet, time.time(), 0)

        if debug:

            print(f"[SENDER] Sent Packet {next_seq}")

        next_seq += 1



    try:

        header, payload, addr = recv_packet(sock, debug=debug)

        timeout_count = 0



        if header["Conn ID"] != CONN_ID:

            if debug:

                print(f"[SENDER] Dropped packet with wrong Conn ID: {header['Conn ID']}")

            continue



        ack_no = header["Ack No"]

        seq_no = header["Seq No"]

        flags = header["Flags"]



        if ack_no > 0 and ack_no <= len(acked_packets):

            for i in range(base, ack_no + 1):

                if not acked_packets[i - 1]:

                    acked_packets[i - 1] = True

                    if i in sent_packets:

                        send_time = sent_packets[i][1]

                        rtt_samples.append(time.time() - send_time)

                        if debug:

                            print(f"[SENDER] Received ACK {i}, RTT={rtt_samples[-1]:.3f}s")

                        del sent_packets[i]

            while base <= len(acked_packets) and acked_packets[base - 1]:

                base += 1

            if base > len(SENDER_MESSAGES) and state == "OPEN":

                state = "CLOSING"

                if debug:

                    print("[SENDER] All packets ACKed, moving to CLOSING")



        if flags in (0, 1) and payload and seq_no > 0:

            if seq_no not in receiver_packets:

                receiver_packets[seq_no] = payload.decode()

                if debug:

                    print(f"[SENDER] Received Receiver Packet {seq_no}: {payload.decode()}")

            else:

                if debug:

                    print(f"[SENDER] Duplicate Receiver Packet {seq_no}")

            ack_packet = serialize_packet(CONN_ID, 0, seq_no, b"", 1, 255)

            send_packet(sock, addr, ack_packet, debug=debug)

            if debug:

                print(f"[SENDER] Sent ACK {seq_no} for Receiver's data")

            while next_expected_receiver_seq in receiver_packets:

                if debug:

                    print(f"[SENDER] Delivered Receiver Packet {next_expected_receiver_seq}")

                next_expected_receiver_seq += 1



        if flags == 5 and state == "CLOSING":

            if debug:

                print("[SENDER] Received FIN+ACK")

            fin_packet = serialize_packet(CONN_ID, 0, 0, b"", 4, 255)

            send_packet(sock, addr, fin_packet, debug=debug)

            if debug:

                print(f"[SENDER] Sent FIN in response to FIN+ACK")

            state = "CLOSED"



    except socket.timeout:

        timeout_count += 1

        if timeout_count >= MAX_TIMEOUTS:

            if debug:

                print(f"[SENDER] No packets received after {MAX_TIMEOUTS * 0.2:.1f}s, closing")

            state = "CLOSED"

            continue

        if state == "OPEN":

            current_time = time.time()

            rto = estimate_rto(rtt_samples)

            for seq in list(sent_packets.keys()):

                packet, send_time, retries = sent_packets[seq]

                if current_time - send_time >= rto:

                    if retries >= MAX_RETRIES:

                        if debug:

                            print(f"[SENDER] Packet {seq} dropped after {retries} retries")

                        acked_packets[seq - 1] = True

                        del sent_packets[seq]

                        while base <= len(acked_packets) and acked_packets[base - 1]:

                            base += 1

                        if base > len(SENDER_MESSAGES):

                            state = "CLOSING"

                        continue

                    packet = serialize_packet(CONN_ID, seq, 0, 

                                             SENDER_MESSAGES[seq - 1].encode(), 0, 255)

                    send_packet(sock, receiver_addr, packet, debug=debug)

                    sent_packets[seq] = (packet, time.time(), retries + 1)

                    if debug:

                        print(f"[SENDER] Timeout, resent Packet {seq}, retries={retries + 1}")

        elif state == "CLOSING":

            if "fin_retries" not in locals():

                fin_retries = 0

                fin_sent_time = 0

            if time.time() - fin_sent_time >= FIN_TIMEOUT:

                if fin_retries >= MAX_FIN_RETRIES:

                    if debug:

                        print("[SENDER] Max FIN retries reached, moving to CLOSED")

                    state = "CLOSED"

                    continue

                fin_packet = serialize_packet(CONN_ID, 0, 0, b"", 4, 255)

                send_packet(sock, receiver_addr, fin_packet, debug=debug)

                if debug:

                    print(f"[SENDER] Sent FIN, attempt {fin_retries + 1}")

                fin_retries += 1

                fin_sent_time = time.time()

    except OSError as e:

        if state == "CLOSING":

            if debug:

                print(f"[SENDER] Connection closed by receiver, moving to CLOSED")

            state = "CLOSED"

            continue

        if debug:

            print(f"[SENDER] Receive error: {e}")

        continue

    except ValueError as e:

        if debug:

            print(f"[SENDER] Invalid packet: {e}")

        continue



sock.close()

if debug:

    print("[SENDER] Closed")

if name == "main":

main(debug=True)
