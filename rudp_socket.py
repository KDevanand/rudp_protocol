import socket

from packet import deserialize_packet

def send_packet(sock, address, packet, debug=False):

try:

    sock.sendto(packet, address)

except OSError as e:

    raise OSError(f"Failed to send packet to {address}: {e}")

def recv_packet(sock, debug=False):

try:

    packet, addr = sock.recvfrom(1024)

    header, payload = deserialize_packet(packet)

    return header, payload, addr

except socket.timeout:

    raise socket.timeout

except OSError as e:

    raise OSError(f"Failed to receive packet: {e}")

except ValueError as e:

    raise ValueError(f"Invalid packet received: {e}")
