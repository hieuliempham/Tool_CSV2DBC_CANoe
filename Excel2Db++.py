import csv

# Define input and output file paths
signal_csv = 'BMS-Charger-Signal.csv'  # Path to the signal CSV
msg_csv = 'BMS-Charger-Message.csv'        # Path to the message CSV
dbc_file = 'output.dbc'                # Output DBC file

# Parse the message CSV to collect message data
messages = {}
with open(msg_csv, 'r') as f:
    reader = csv.DictReader(f)
    
    for row in reader:
        message_id = row['ID']
        message_name = row['Name']
        dlc = row['DLC [Byte]']
        transmitter = row['Transmitter']
        comment = row['Comment']
        
        # Add each message to the dictionary
        messages[message_id] = {
            'name': message_name,
            'dlc': dlc,
            'transmitter': transmitter,
            'comment': comment,
            'signals': []  # Empty list to hold signals
        }

# Parse the signal CSV to collect signal data
with open(signal_csv, 'r') as f:
    reader = csv.DictReader(f)
    
    for row in reader:
        message_id = row['Message ID']
        signal_name = row['Name']
        start_bit = row['Startbit']
        length = row['Length [Bit]']
        comment = row['Comment']
        
        # If the message is in the messages dictionary, add the signal
        if message_id in messages:
            messages[message_id]['signals'].append({
                'name': signal_name,
                'start_bit': start_bit,
                'length': length,
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
        # Convert message ID to decimal
        message_id_dec = int(message_id, 16)
        f.write(f"BO_ {message_id_dec} {message['name']}: {message['dlc']} {message['transmitter']}\n")
        
        for signal in message['signals']:
            f.write(f" SG_ {signal['name']} : {signal['start_bit']}|{signal['length']}@1+ (1,0) [0|0] \"\" {message['transmitter']}\n")
        
        # Add a comment for the message if present
        if message['comment']:
            f.write(f"CM_ BO_ {message_id_dec} \"{message['comment']}\";\n")

    f.write('\n')

print("Conversion completed! DBC file created.")
