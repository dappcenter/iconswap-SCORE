import json
import sys

if __name__ == '__main__':
    network = sys.argv[1]
    contract1 = sys.argv[2]
    contract2 = sys.argv[3]
    amount1 = sys.argv[4]
    amount2 = sys.argv[5]

    score_address_txt = "./config/" + network + "/score_address.txt"

    call = json.loads(open("./calls/create_swap.json", "rb").read())
    call["params"]["to"] = open(score_address_txt, "r").read()

    call["params"]["data"]["params"]["contract1"] = contract1
    call["params"]["data"]["params"]["contract2"] = contract2
    call["params"]["data"]["params"]["amount1"] = amount1
    call["params"]["data"]["params"]["amount2"] = amount2

    print(json.dumps(call))
