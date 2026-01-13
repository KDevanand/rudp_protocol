import struct
import zlib

def generate_checksum(data):

return zlib.crc32(data)

def serialize_packet(conn_id, seq_no, ack_no, payload, flags, ttl):

if not (0 <= conn_id <= 0xFFFFFF):

    raise ValueError(f"conn_id {conn_id} out of range (0 to 16777215)")

if not (0 <= seq_no <= 0xFFFFFF):

    raise ValueError(f"seq_no {seq_no} out of range (0 to 16777215)")

if not (0 <= ack_no <= 0xFFFFFF):

    raise ValueError(f"ack_no {ack_no} out of range (0 to 16777215)")

if not (0 <= flags <= 0xFF):

    raise ValueError(f"flags {flags} out of range (0 to 255)")

if not (0 <= ttl <= 0xFF):

    raise ValueError(f"ttl {ttl} out of range (0 to 255)")



payload_len = len(payload)

if payload_len > 0xFFFF:

    raise ValueError(f"Payload size {payload_len} exceeds max (65535 bytes)")



header = struct.pack("!3s3s3sBB", 

                     conn_id.to_bytes(3, 'big'),

                     seq_no.to_bytes(3, 'big'),

                     ack_no.to_bytes(3, 'big'),

                     flags, ttl)



assert len(header) == 11, f"Header size mismatch: got {len(header)} bytes, expected 11"



packet_data = header + struct.pack("!H", payload_len) + payload



checksum = generate_checksum(packet_data)

packet_data += struct.pack("!I", checksum)



return packet_data

def deserialize_packet(packet_data, debug=False):

min_header_size = 11  #                                                                                                                   Header: 3s3s3sBB

min_packet_size = min_header_size + 2 + 4  #                                                                                              Header + payload_len (2B) + checksum (4B)



if len(packet_data) < min_packet_size:

    if debug:

        print(f"[PACKET] Invalid packet: too small, got {len(packet_data)} bytes, expected {min_packet_size}, data={packet_data.hex()}")

    raise ValueError(f"Packet too small: got {len(packet_data)} bytes, expected at least {min_packet_size} bytes")



header_data = packet_data[:min_header_size]

if len(header_data) != min_header_size:

    if debug:

        print(f"[PACKET] Invalid header: got {len(header_data)} bytes, expected {min_header_size}, data={header_data.hex()}")

    raise ValueError(f"Header too small: got {len(header_data)} bytes, expected {min_header_size} bytes")



try:

    header = struct.unpack("!3s3s3sBB", header_data)

except struct.error as e:

    if debug:

        print(f"[PACKET] Failed to unpack header: got {len(header_data)} bytes, expected {min_header_size}, error={e}, data={header_data.hex()}")

    raise ValueError(f"Failed to unpack header: got {len(header_data)} bytes, expected {min_header_size} bytes, error: {e}")



payload_len = struct.unpack("!H", packet_data[min_header_size:min_header_size + 2])[0]

expected_size = min_packet_size + payload_len

if len(packet_data) != expected_size:

    if debug:

        print(f"[PACKET] Size mismatch: got {len(packet_data)} bytes, expected {expected_size}, data={packet_data.hex()}")

    raise ValueError(f"Packet size mismatch: got {len(packet_data)} bytes, expected {expected_size} bytes")



payload = packet_data[min_header_size + 2:min_header_size + 2 + payload_len]

received_checksum = struct.unpack("!I", packet_data[-4:])[0]

computed_checksum = generate_checksum(packet_data[:-4])

if computed_checksum != received_checksum:

    if debug:

        print(f"[PACKET] Checksum mismatch: got {received_checksum}, computed {computed_checksum}, data={packet_data.hex()}")

    raise ValueError(f"Checksum mismatch: got {received_checksum}, computed {computed_checksum}")



return {

    "Conn ID": int.from_bytes(header[0], 'big'),

    "Seq No": int.from_bytes(header[1], 'big'),

    "Ack No": int.from_bytes(header[2], 'big'),

    "Flags": header[3],

    "TTL": header[4],

    "Payload Length": payload_len

}, payload

def reduce_ttl(packet_data, debug=False):

header, payload = deserialize_packet(packet_data, debug=debug)

if header["TTL"] == 0:

    raise ValueError("TTL already expired")



return serialize_packet(

    conn_id=header["Conn ID"],

    seq_no=header["Seq No"],

    ack_no=header["Ack No"],

    payload=payload,

    flags=header["Flags"],

    ttl=header["TTL"] - 1

)
