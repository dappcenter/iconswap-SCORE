#!/bin/bash

. ./scripts/utils/utils.sh

function print_usage {
    usage_header ${0}
    usage_option " -n <network> : Network to use (localhost, yeouido, euljiro or mainnet)"
    usage_option " -c <contract> : contract address to delete"
    usage_footer
    exit 1
}

function process {

    if [[ ("$network" == "") || ("$contract" == "") ]]; then
        print_usage
    fi

    command=$(cat <<-COMMAND
    tbears sendtx <(
        python ./scripts/score/dynamic_call/remove_whitelist.py
            ${network@Q}
            ${contract@Q}
        )
        -c ./config/${network}/tbears_cli_config.json
COMMAND
)

    txresult=$(./scripts/icon/txresult.sh -n "${network}" -c "${command}")
    echo -e "${txresult}"
}

# Parameters
while getopts "n:c:" option; do
    case "${option}" in
        n)
            network=${OPTARG}
            ;;
        c)
            contract=${OPTARG}
            ;;
        *)
            print_usage 
            ;;
    esac 
done
shift $((OPTIND-1))

process