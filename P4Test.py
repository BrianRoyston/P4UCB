from P4 import P4,P4Exception 

p4 = P4()                        # Create the P4 instance
p4.port = "209.129.168.15:1666"
p4.user = "Brian"
p4.password = "UCBFall2022"
p4.client = "BrianPerforceWS"            # Set some environment variables

p4.connect()
p4.run_login()

file = open("test.txt", "w")

info = p4.run( "info" )        # Run "p4 info" (returns a dict)
for key in info[0]:            # and display all key-value pairs
    file.write(str(key) + "=" + str(info[0][key]) + '\n')

file.close()