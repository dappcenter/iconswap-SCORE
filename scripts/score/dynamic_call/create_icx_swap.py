import json
import sys

if __name__ == '__main__':
    network = sys.argv[1]
    maker_amount = sys.argv[2]
    taker_contract = sys.argv[3]
    taker_amount = sys.argv[4]

    score_address_txt = "./config/" + network + "/score_address.txt"

    call = json.loads(open("./calls/create_icx_swap.json", "rb").read())
    call["params"]["to"] = open(score_address_txt, "r").read()

    call["params"]["value"] = "%#x" % int(maker_amount, 10)
    call["params"]["data"]["params"]["taker_contract"] = taker_contract
    call["params"]["data"]["params"]["taker_amount"] = taker_amount

    print(json.dumps(call))
