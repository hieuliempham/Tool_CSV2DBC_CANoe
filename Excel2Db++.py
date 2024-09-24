import csv

# Define input and output file paths
signal_csv = 'Signal.csv'  # Path to the signal CSV
msg_csv = 'Message.csv'    # Path to the message CSV
dbc_file = 'output.dbc'    # Output DBC file
max_gen_msg_cycle_time = float('-inf')  # Start with negative infinity to find max

# Set to collect unique GenMsgSendType values
genMsgSendType_set = set()
genSigSendType_set = set()

# Parse the message CSV to collect message data
messages = {}
network_nodes = {}

with open(msg_csv, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        message_id = row['ID']
        message_id_dec = int(message_id, 16)

        # Handle extended CAN IDs
        if row['ID-Format'] == 'CAN Extended':
            message_id_dec |= 0x80000000

        # Get GenMsgCycleTime and update the max value
        msg_cycle_time = row['GenMsgCycleTime']
        if msg_cycle_time:
            try:
                cycle_time_value = float(msg_cycle_time)
                max_gen_msg_cycle_time = max(max_gen_msg_cycle_time, cycle_time_value)
            except ValueError:
                print(f"Invalid GenMsgCycleTime for message ID: {message_id}")

        # Collect unique GenMsgSendType values
        msg_send_type = row['GenMsgSendType']
        if msg_send_type:
            genMsgSendType_set.add(msg_send_type)  # Add unique values to the set

        # Store message data
        messages[message_id] = {
            'name': row['Name'],
            'dlc': row['DLC [Byte]'],
            'transmitter': row['Transmitter'],
            'reciever': row['Reciever'],
            'msg_comment': row['Comment'],
            'genMsgSendType': msg_send_type,
            'genMsgCycleTime': msg_cycle_time,
            'signals': []
        }

# Parse the signal CSV to collect signal data
with open(signal_csv, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        message_id = row['Message ID']
        if message_id in messages:
            # Calculate min/max values based on signedness
            length = int(row['Length [Bit]'])
            factor = float(row.get('Factor', '1'))
            offset = float(row.get('Offset', '0'))
            signedness = row.get('Signedness', '-')

            # Collect unique GenSigSendType values
            signal_send_type = row['GenSigSendType']
            if signal_send_type:
                genSigSendType_set.add(signal_send_type)  # Add unique values to the set

            is_signed = signedness == '-'
            min_val = row['Min'] if 'Min' in row else str(-(2**(length - 1)) * factor + offset) if is_signed else '0'
            max_val = row['Max'] if 'Max' in row else str((2**(length - 1) - 1) * factor + offset) if is_signed else str((2**length - 1) * factor + offset)

            # Append signal to the message
            messages[message_id]['signals'].append({
                'name': row['Name'],
                'start_bit': int(row['Startbit']),
                'length': length,
                'min': min_val,
                'max': max_val,
                'byte_order': row.get('ByteOrder', '1'),
                'signedness': signedness,
                'factor': factor,
                'offset': offset,
                'genSigSendType': signal_send_type,
                'signal_comment': row.get('Comment')
            })

# Convert the set to a list for indexing
genMsgSendType_list = list(genMsgSendType_set)
genSigSendType_list = list(genSigSendType_set)

# Write the DBC file
with open(dbc_file, 'w') as f:
    f.write('VERSION ""\n\nNS_ :\n\nBS_ :\n\n')

    # Write nodes (BU_)
    nodes = {message['transmitter'] for message in messages.values()}
    f.write(f"BU_: {' '.join(nodes)}\n\n")

    # Write messages and signals (BO_ and SG_)
    for message_id, message in messages.items():
        message_id_dec = int(message_id, 16)
        f.write(f"BO_ {message_id_dec} {message['name']}: {message['dlc']} {message['transmitter']}\n")
        for signal in message['signals']:
            f.write(
                f" SG_ {signal['name']} : {signal['start_bit']}|{signal['length']}@{signal['byte_order']}{signal['signedness']} "
                f"({signal['factor']},{signal['offset']}) [{signal['min']}|{signal['max']}] \"\" {message['reciever']}\n"
            )

    # Write comments for messages and signals
    for message_id, message in messages.items():
        message_id_dec = int(message_id, 16)

        # Message-level comment
        if message['msg_comment']:
            f.write(f"CM_ BO_ {message_id_dec} \"{message['msg_comment']}\";\n")

        # Signal-level comments
        for signal in message['signals']:
            if signal['signal_comment']:
                f.write(f"CM_ SG_ {message_id_dec} {signal['name']} \"{signal['signal_comment']}\";\n")

    # Write dynamic attributes
    unique_gen_msg_send_types = ",".join(f'"{msg}"' for msg in genMsgSendType_list)
    f.write(f'BA_DEF_ BO_ "GenMsgSendType" ENUM {unique_gen_msg_send_types};\n')
    unique_gen_sig_send_types = ",".join(f'"{sig}"' for sig in genSigSendType_list)
    f.write(f'BA_DEF_ SG_ "GenSigSendType" ENUM {unique_gen_sig_send_types};\n')
    f.write(f'BA_DEF_ BO_ "GenMsgCycleTime" INT 0 {int(max_gen_msg_cycle_time)};\n')

    # Add message-level attributes
    for message_id, message in messages.items():
        message_id_dec = int(message_id, 16)

        # GenMsgSendType
        if message['genMsgSendType']:
            # Find the index of the GenMsgSendType in the list and write the index instead of the string
            gen_msg_send_type_index = genMsgSendType_list.index(message['genMsgSendType'])
            f.write(f"BA_ \"GenMsgSendType\" BO_ {message_id_dec} {gen_msg_send_type_index};\n")

        # GenMsgCycleTime
        if message['genMsgCycleTime']:
            f.write(f"BA_ \"GenMsgCycleTime\" BO_ {message_id_dec} {message['genMsgCycleTime']};\n")

        for signal in message['signals']:
            if signal['genSigSendType']:
                # Find the index of the GenSigSendType in the list and write the index instead of the string
                gen_sig_send_type_index = genSigSendType_list.index(signal['genSigSendType'])
                f.write(f"BA_ \"GenSigSendType\" SG_ {message_id_dec} {signal['name']} {gen_sig_send_type_index};\n")


print("Conversion completed! DBC file created.")
