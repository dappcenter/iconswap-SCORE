#!/bin/bash

. ./scripts/utils/utils.sh

function print_usage {
    usage_header ${0}
    usage_option " -n <network> : Network to use (localhost, yeouido, euljiro or mainnet)"
    usage_option " -m <maker_amount> : Maker ICX amount"
    usage_option " -c <maker_contract> : Maker contract"
    usage_option " -a <taker_amount> : Taker Amount"
    usage_footer
    exit 1
}

function process {

    if [[ ("$network" == "") || ("$maker_amount" == "") || ("$maker_contract" == "") || ("$taker_amount" == "") ]]; then
        print_usage
    fi

    command=$(cat <<-COMMAND
    tbears sendtx <(
        python ./scripts/score/dynamic_call/create_irc2_swap.py
            ${network@Q}
            ${maker_amount@Q}
            ${maker_contract@Q}
            ${taker_amount@Q}
        )
        -c ./config/${network}/tbears_cli_config.json
COMMAND
)

    txresult=$(./scripts/icon/txresult.sh -n "${network}" -c "${command}")
    echo -e "${txresult}"
}

# Parameters
while getopts "n:c:a:m:" option; do
    case "${option}" in
        n)
            network=${OPTARG}
            ;;
        c)
            maker_contract=${OPTARG}
            ;;
        m)
            maker_amount=${OPTARG}
            ;;
        a)
            taker_amount=${OPTARG}
            ;;
        *)
            print_usage 
            ;;
    esac 
done
shift $((OPTIND-1))

process