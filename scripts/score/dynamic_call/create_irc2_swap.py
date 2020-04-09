import json
import sys

if __name__ == '__main__':
    network = sys.argv[1]
    maker_amount = sys.argv[2]
    maker_contract = sys.argv[3]
    taker_amount = sys.argv[4]

    score_address_txt = "./config/" + network + "/score_address.txt"

    call = json.loads(open("./calls/create_irc2_swap.json", "rb").read())
    call["params"]["to"] = maker_contract

    call["params"]["data"]["params"]["_to"] = open(score_address_txt, "r").read()
    call["params"]["data"]["params"]["_value"] = "%#x" % int(maker_amount)
    call["params"]["data"]["params"]["_data"]["taker_amount"] = hex(int(taker_amount))
    call["params"]["data"]["params"]["_data"] = "0x" + str(call["params"]["data"]["params"]["_data"]).replace('\'', '"').encode('utf-8').hex()
    print(json.dumps(call, indent=4))
