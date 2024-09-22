import csv

# Define input and output file paths
signal_csv = 'BMS-Charger-Signal.csv'  # Path to the signal CSV
msg_csv = 'BMS-Charger-Message.csv'    # Path to the message CSV
dbc_file = 'output.dbc'                # Output DBC file

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
        comment = row['Comment']
        
        # Add each message to the dictionary
        messages[message_id] = {
            'name': message_name,
            'dlc': dlc,
            'transmitter': transmitter,
            'destination' : destination,
            'comment': comment,
            'signals': []  # Empty list to hold signals
        }

        # Add each node to the dictionary
        network_nodes[source] = {
            'name': transmitter,
        }

# Parse the signal CSV to collect signal data
with open(signal_csv, 'r') as f:
    reader = csv.DictReader(f)
    
    for row in reader:
        message_id = row['Message ID']
        signal_name = row['Name']
        start_bit = int(row['Startbit'])  # Convert to integer
        length = int(row['Length [Bit]']) # Convert to integer
        min_val = row['Min'] if 'Min' in row else '0'  # Get min value if available, otherwise 0
        max_val = row['Max'] if 'Max' in row else str(2**length - 1)  # Set max based on bit length
        byte_order = row.get('ByteOrder', '1')  # Use ByteOrder if available, otherwise default to big-endian
        signedness = row.get('Signedness', '-')  # Use Signedness if available, otherwise default to unsigned
        factor = row.get('Factor', '1')  # Factor from CSV or default to 1
        offset = row.get('Offset', '0')  # Offset from CSV or default to 0
        comment = row['Comment']
        
        # If the message is in the messages dictionary, add the signal
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
                'comment': comment
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
        # Convert message ID to decimal
        message_id_dec = int(message_id, 16)
        f.write(f"BO_ {message_id_dec} {message['name']}: {message['dlc']} {message['transmitter']}\n")
        
        for signal in message['signals']:
            # Write each signal with its proper min/max values, byte order, signedness, etc.
            f.write(
                f" SG_ {signal['name']} : {signal['start_bit']}|{signal['length']}@{signal['byte_order']}{signal['signedness']} "
                f"({signal['factor']},{signal['offset']}) [{signal['min']}|{signal['max']}] \"\" {network_nodes[message['destination']]['name']}\n"
            )
        
        
    f.write('\n')
    for message_id, message in messages.items():
        # Add a comment for the message if present
        if message['comment']:
            f.write(f"CM_ BO_ {message_id_dec} \"{message['comment']}\";\n")

    f.write('\n')

print("Conversion completed! DBC file created.")
