import argparse
from secureconfig.secureconfigparser import SecureConfigParser
from secureconfig.cryptkeeper import CryptKeeper

def main():
    # Main function.
    parser=argparse.ArgumentParser("Generates encrypted credentials")
    parser.add_argument('--secret-file',help='Name of the file to store the secret encrypted credentials',required=True)
    parser.add_argument('--unencrypted-credentials',help='Name of the file that currently stores unencrypted credentials')
    parser.add_argument('--key-file',help="Specifies the name of the file where to store the secret key that will unlock the secret file",required=True)
    args=vars(parser.parse_args())
    ck=CryptKeeper()
    key=ck.generate_key()
    # Now, if we received the argument generate-key, let's generate the file
    scfg=SecureConfigParser.from_key(key)
    scfg.read(args["unencrypted_credentials"])
    username=scfg.get('credentials','username')
    password=scfg.get('credentials','password')
    scfg.set('credentials','username',username,encrypt=True)
    scfg.set('credentials','password',password,encrypt=True)
    file=open(args['secret_file'],"w")
    scfg.write(file)
    file.close()
    # Now we store the secret key
    secret_file=open(args['key_file'],"w")
    secret_file.write(key)
    secret_file.close()
# Invoke main function upon execution
if __name__=="__main__":
    main()