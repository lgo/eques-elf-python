package main

import "fmt"
import "time"
import "net"
import "regexp"
import "flag"
import "os"
import "crypto/aes"
import "encoding/hex"


var devices = make([]string, 0)

func thisTime()(epochTime int64, parsedTime string) {
	now := time.Now()
	epochTime = now.Unix()
	parsedTime = fmt.Sprintf("%d-%02d-%02d-%02d:%02d:%02d", now.Year(), now.Month(), now.Day(), now.Hour(), now.Minute(), now.Second())
	return
}

//Function to send UDP broadcast messages
func udpBroadcaster(listenaddress net.UDPAddr, broadcastaddress net.UDPAddr, command []byte) {

	localaddress := listenaddress
	remoteaddress := broadcastaddress

	connection, err := net.DialUDP("udp", &localaddress, &remoteaddress)
	
	if err != nil {
	    panic(err)
	}

	defer connection.Close()

	connection.Write(command)
}

//Function to listen UDP responses
func udpBroadcastListen (listenaddress net.UDPAddr) {
	localaddress := listenaddress
	deviceCheck := false
	connection, err := net.ListenUDP("udp", &localaddress)
	
	if err != nil {
	    panic(err)
	}

	defer connection.Close()

	for {
		udpbuffer := make([]byte, 1024)

		deadline := time.Now().Add(3 * time.Second)
		err = connection.SetReadDeadline(deadline)

		length, addr, err := connection.ReadFromUDP(udpbuffer)
		if err != nil {
    	    fmt.Printf("\nRetrying\n\n")
    	    break
		} else {
			fmt.Printf("%s\n", addr)
			plaintext := hex.EncodeToString(udpbuffer[:length])
			//fmt.Println(plaintext)
			decrypted := aesEcb256Decrypt(plaintext)
			fmt.Printf("%s\n", decrypted)

			for _, n := range devices {
				if addr.IP.String() + ": " + decrypted == n {
					deviceCheck = true
				} 
			}
			if !deviceCheck {
				devices = append(devices, addr.IP.String() + ": " + decrypted)
			}
		}
	}
}

//Function to send UDP targeted messages
func udpClient(remoteaddress net.UDPAddr, command []byte) {

	plugaddress := remoteaddress

	connection, err := net.DialUDP("udp", nil, &plugaddress)
	
	if err != nil {
	    panic(err)
	}

	defer connection.Close()

	connection.Write(command)

	udpbuffer := make([]byte, 1024)
	length, addr, err := connection.ReadFrom(udpbuffer)
	if err != nil {
        panic(err)
	} else {
		fmt.Printf("%s\n", addr)
		plaintext := hex.EncodeToString(udpbuffer[:length])
		decrypted := aesEcb256Decrypt(plaintext)
		fmt.Printf("%s\n", decrypted)
	}
}

//AES 256 Encryption using the key fdsl;mewrjope456fds4fbvfnjwaugfo
func aesEcb256Encrypt(parsedCommand string) (string) {
        key, _ := hex.DecodeString("6664736c3b6d6577726a6f706534353666647334666276666e6a77617567666f")

        bs := 16

	var plaintext []byte
	nopadplaintext := []byte(parsedCommand)
        pad := bs - len(nopadplaintext) % bs

	if pad != 16 {
		paddedlength := len(nopadplaintext) + pad
		paddedplaintext := make([]byte, paddedlength)
		copy(paddedplaintext, nopadplaintext)

		plaintext = paddedplaintext

	} else {
		plaintext = []byte(parsedCommand)
		}

        block, err := aes.NewCipher(key)
        if err != nil {
                panic(err)
        }

        ciphertext := make([]byte, len(plaintext))
	be := 0
        for len(plaintext) > 0 {
                block.Encrypt(ciphertext[be:], plaintext)
                plaintext = plaintext[bs:]
                be += bs
        }
	return hex.EncodeToString(ciphertext)
}

//AES 256 Decryption using the key fdsl;mewrjope456fds4fbvfnjwaugfo
func aesEcb256Decrypt(commandResponse string) (string) {
        key, _ := hex.DecodeString("6664736c3b6d6577726a6f706534353666647334666276666e6a77617567666f")

        bs := 16

	var ciphertext []byte
	nopadciphertext, _ := hex.DecodeString(commandResponse)
        pad := bs - len(nopadciphertext) % bs

	if pad != 16 {
		paddedlength := len(nopadciphertext) + pad
		paddedciphertext := make([]byte, paddedlength)
		copy(paddedciphertext, nopadciphertext)

		ciphertext = paddedciphertext

	} else {
		ciphertext, _ = hex.DecodeString(commandResponse)
		}

        block, err := aes.NewCipher(key)
        if err != nil {
                panic(err)
        }

        plaintext := make([]byte, len(ciphertext))
	be := 0
        for len(ciphertext) > 0 {
		block.Decrypt(plaintext[be:], ciphertext)
                ciphertext = ciphertext[bs:]
                be += bs
        }
	return string(plaintext)
}

func main() {

	_, parsedTime := thisTime()
	var command string
	macPtr := flag.String("mac", "", "Mac address of the eques plug in the format aa-bb-cc-dd-ee-ff")
	commandPtr := flag.String("command", "", "Either of: [disover](no other parameters needed); [status; timer; on; off](mac,ip and pass needed)")
	ipPtr := flag.String("ip", "", "ip: IP address of the smart power plug")
	passPtr := flag.String("pass", "", "pass: Password of the smart power plug")

	flag.Parse()

    if *commandPtr == "" {  
    	fmt.Println("the command must be specified\n")  		
    	flag.PrintDefaults()
        os.Exit(1)
    }

	switch *commandPtr {
		case "discover":
			count := 1
			for count < 10 {

				command = "lan_phone%mac%nopassword%"+parsedTime+"%heart"
				ciphertext := aesEcb256Encrypt(command)

				//fmt.Println(epochTime)
				fmt.Println("Sending Command:", command)
				fmt.Println("Sending Encoded Command:", ciphertext)

				encodedCommand, _ := hex.DecodeString(ciphertext)

				listenaddress := net.UDPAddr{
	    			Port: 2000,
	    			IP: net.ParseIP("0.0.0.0"),
				}
	
				broadcastaddress := net.UDPAddr{
	    			Port: 27431,
	    			IP: net.ParseIP("255.255.255.255"),
				}
		
				udpBroadcaster(listenaddress, broadcastaddress, encodedCommand)	

				fmt.Println("\nReceiving\n")
				udpBroadcastListen(listenaddress)
				//time.Sleep(3 * time.Second)

				count += 1
			}
			separator := regexp.MustCompile(`%`)
			fmt.Println("\n====================\n")
			fmt.Println("Discovered devices: ", len(devices))

			for _, n := range devices {
				separatedValues := separator.Split(n, -1)
				fmt.Println(separatedValues)
			}

		case "status":
			command = "lan_phone%"+*macPtr+"%"+*passPtr+"%check%relay"
			ciphertext := aesEcb256Encrypt(command)
			encodedCommand, _ := hex.DecodeString(ciphertext)

			fmt.Println("Sending Command:", command)
			fmt.Println("Sending Encoded Command:", ciphertext)

			remoteaddress := net.UDPAddr{
	    		Port: 27431,
	    		IP: net.ParseIP(*ipPtr),
			}
			udpClient(remoteaddress, encodedCommand)


		case "timer":
			command = "lan_phone%"+*macPtr+"%"+*passPtr+"%check#total%timer"
			ciphertext := aesEcb256Encrypt(command)
			encodedCommand, _ := hex.DecodeString(ciphertext)

			fmt.Println("Sending Command:", command)
			fmt.Println("Sending Encoded Command:", ciphertext)

			remoteaddress := net.UDPAddr{
	    		Port: 27431,
	    		IP: net.ParseIP(*ipPtr),
			}
		
			udpClient(remoteaddress, encodedCommand)

		case "on":
			command = "lan_phone%"+*macPtr+"%"+*passPtr+"%open%relay"
			ciphertext := aesEcb256Encrypt(command)
			encodedCommand, _ := hex.DecodeString(ciphertext)

			fmt.Println("Sending Command:", command)
			fmt.Println("Sending Encoded Command:", ciphertext)

			remoteaddress := net.UDPAddr{
	    		Port: 27431,
	    		IP: net.ParseIP(*ipPtr),
			}
		
			udpClient(remoteaddress, encodedCommand)

		case "off":
			command = "lan_phone%"+*macPtr+"%"+*passPtr+"%close%relay"
			ciphertext := aesEcb256Encrypt(command)
			encodedCommand, _ := hex.DecodeString(ciphertext)

			fmt.Println("Sending Command:", command)
			fmt.Println("Sending Encoded Command:", ciphertext)

			remoteaddress := net.UDPAddr{
	    		Port: 27431,
	    		IP: net.ParseIP(*ipPtr),
			}
		
			udpClient(remoteaddress, encodedCommand)

		default:
    		fmt.Println("Wrong command argument(s) specified\n")
    		flag.PrintDefaults()
    		os.Exit(1)
    }
}
