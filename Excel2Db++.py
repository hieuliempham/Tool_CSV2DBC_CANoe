import csv

# Define input and output file paths
signal_csv = 'BMS-Charger-Signal.csv'  # Path to the signal CSV
msg_csv = 'BMS-Charger-Message.csv'    # Path to the message CSV
dbc_file = 'output.dbc'                # Output DBC file
max_gen_msg_cycle_time = float('-inf')  # Start with negative infinity to ensure any value will be larger

# Parse the message CSV to collect message data
messages = {}
network_nodes = {}

with open(msg_csv, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        message_id = row['ID']
        message_name = row['Name']
        dlc = row['DLC [Byte]']
        transmitter = row['Transmitter']
        source = row['Source']
        destination = row['Destination']
        msg_comment = row['Comment']
        msg_attribute_GenMsgSendType = row['GenMsgSendType']
        msg_attribute_GenMsgCycleTime = row['GenMsgCycleTime']
        if msg_attribute_GenMsgCycleTime:
            try:
                cycle_time_value = float(msg_attribute_GenMsgCycleTime)  # Convert to float (or int if you prefer)
                # Update the max value if the current cycle time is larger
                if cycle_time_value > max_gen_msg_cycle_time:
                    max_gen_msg_cycle_time = cycle_time_value
            except ValueError:
                print(f"Invalid GenMsgCycleTime value: {msg_attribute_GenMsgCycleTime} for message ID: {message_id}")


        # Add each message to the dictionary
        messages[message_id] = {
            'name': message_name,
            'dlc': dlc,
            'transmitter': transmitter,
            'destination': destination,
            'msg_comment': msg_comment,
            'genMsgSendType': msg_attribute_GenMsgSendType,
            'genMsgCycleTime': msg_attribute_GenMsgCycleTime,
            'signals': []  # Empty list to hold signals
        }

        # Add each node to the dictionary
        network_nodes[source] = {'name': transmitter}

# Parse the signal CSV to collect signal data
with open(signal_csv, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        message_id = row['Message ID']
        signal_name = row['Name']
        start_bit = int(row['Startbit'])  # Convert to integer
        length = int(row['Length [Bit]'])  # Convert to integer
        signedness = row.get('Signedness', '-')  # Default to signed
        is_signed = signedness == '-'  # Signed flag
        byte_order = row.get('ByteOrder', '1')  # Default to big-endian
        factor = float(row.get('Factor', '1'))  # Ensure factor is a float
        offset = float(row.get('Offset', '0'))  # Ensure offset is a float

        # Set min and max values based on signedness
        if is_signed:
            min_val = row['Min'] if 'Min' in row else str((-(2**(length - 1)) * factor) + offset)
            max_val = row['Max'] if 'Max' in row else str(((2**(length - 1) - 1) * factor) + offset)
        else:
            min_val = row['Min'] if 'Min' in row else str(0)  # Unsigned min
            max_val = row['Max'] if 'Max' in row else str((2**length - 1) * factor + offset)  # Unsigned max

        signal_comment = row.get('Comment')

        # Add signal to the message
        if message_id in messages:
            messages[message_id]['signals'].append({
                'name': signal_name,
                'start_bit': start_bit,
                'length': length,
                'min': min_val,
                'max': max_val,
                'byte_order': byte_order,
                'signedness': signedness,
                'factor': factor,
                'offset': offset,
                'signal_comment': signal_comment
            })

# Write the DBC file
with open(dbc_file, 'w') as f:
    f.write('VERSION ""\n\nNS_ :\n\nBS_ :\n\n')

    # Write nodes (BU_)
    nodes = set([message['transmitter'] for message in messages.values()])
    f.write(f"BU_: {' '.join(nodes)}\n\n")

    # Write messages and signals (BO_ and SG_)
    for message_id, message in messages.items():
        f.write('\n')
        message_id_dec = int(message_id, 16)  # Convert message ID to decimal
        is_extended = message_id_dec > 0x7FF  # Check if it's an extended ID
        if is_extended:
            message_id_dec |= 0x80000000  # Set the extended ID flag

        # Write message (BO_)
        f.write(f"BO_ {message_id_dec} {message['name']}: {message['dlc']} {message['transmitter']}\n")

        # Write signals (SG_)
        for signal in message['signals']:
            f.write(
                f" SG_ {signal['name']} : {signal['start_bit']}|{signal['length']}@{signal['byte_order']}{signal['signedness']} "
                f"({signal['factor']},{signal['offset']}) [{signal['min']}|{signal['max']}] \"\" {network_nodes[message['destination']]['name']}\n"
            )

    f.write('\n')

    # Write comments for messages and signals
    for message_id, message in messages.items():
        # Message-level comment
        if message['msg_comment']:
            message_id_dec = int(message_id, 16)
            if int(message_id_dec) > 0x7FF:
                message_id_dec |= 0x80000000  # Mark extended ID
            f.write(f"CM_ BO_ {message_id_dec} \"{message['msg_comment']}\";\n")


        # Signal-level comments
        for signal in message['signals']:
            if signal['signal_comment']:
                f.write(f"CM_ SG_ {message_id_dec} {signal['name']} \"{signal['signal_comment']}\";\n")

    # Define attributes for messages and signals
    if 'genMsgSendType' in message and message['genMsgSendType']:
        f.write(f'BA_DEF_ BO_  "GenMsgSendType" ENUM "cyclic","reserved","cyclicIfActive","reserved","reserved","reserved","reserved","reserved","noMsgSendType";\n')
        genMsgSendType = ["cyclic", "reserved", "cyclicIfActive", "reserved", "reserved", "reserved", "reserved", "reserved", "noMsgSendType"]
    
    if 'genMsgCycleTime' in message and message['genMsgCycleTime']:
        # f.write(f'BA_DEF_ BO_  "GenMsgCycleTime" INT 0 10000;\n')
        f.write(f'BA_DEF_ BO_  "GenMsgCycleTime" INT 0 {int(max_gen_msg_cycle_time)};\n')

    # Add attributes for messages and signals
    for message_id, message in messages.items():
        # Message-level Attribute
        if 'genMsgSendType' in message and message['genMsgSendType']:
            # Check if the value is in the genMsgSendType list
            if message['genMsgSendType'] in genMsgSendType:
                # Get the index of the value in genMsgSendType list and overwrite it
                genMsgSendTypeIndex = genMsgSendType.index(message['genMsgSendType'])

                message_id_dec = int(message_id, 16)
                if message_id_dec > 0x7FF:
                    message_id_dec |= 0x80000000  # Mark extended ID
                
                # Write the attribute with the object number (index)
                f.write(f"BA_ \"GenMsgSendType\" BO_ {message_id_dec} {genMsgSendTypeIndex};\n")

        if message['genMsgCycleTime']:
            message_id_dec = int(message_id, 16)
            if int(message_id_dec) > 0x7FF:
                message_id_dec |= 0x80000000  # Mark extended ID
            f.write(f"BA_ \"GenMsgCycleTime\" BO_ {message_id_dec} {message['genMsgCycleTime']};\n")
                



print("Conversion completed! DBC file created.")

