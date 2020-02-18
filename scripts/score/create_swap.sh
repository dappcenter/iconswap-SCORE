#!/bin/bash

. ./scripts/utils/utils.sh

function print_usage {
    usage_header ${0}
    usage_option " -n <network> : Network to use (localhost, yeouido, euljiro or mainnet)"
    usage_option " -i <contract1> : contract1"
    usage_option " -j <contract2> : contract2"
    usage_option " -m <amount1> : amount1"
    usage_option " -o <amount2> : amount2"
    usage_footer
    exit 1
}

function process {

    if [[ ("$network" == "") || ("$contract1" == "") || ("$contract2" == "") || ("$amount1" == "") || ("$amount2" == "") ]]; then
        print_usage
    fi

    command=$(cat <<-COMMAND
    tbears sendtx <(
        python ./scripts/score/dynamic_call/create_swap.py
            ${network@Q}
            ${contract1@Q}
            ${contract2@Q}
            ${amount1@Q}
            ${amount2@Q}
        )
        -c ./config/${network}/tbears_cli_config.json
COMMAND
)

    txresult=$(./scripts/icon/txresult.sh -n "${network}" -c "${command}")
    echo -e "${txresult}"
}

# Parameters
while getopts "n:i:j:m:o:" option; do
    case "${option}" in
        n)
            network=${OPTARG}
            ;;
        i)
            contract1=${OPTARG}
            ;;
        j)
            contract2=${OPTARG}
            ;;
        m)
            amount1=${OPTARG}
            ;;
        o)
            amount2=${OPTARG}
            ;;
        *)
            print_usage 
            ;;
    esac 
done
shift $((OPTIND-1))

process