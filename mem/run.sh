#!/bin/bash

function catvmstat
{
    time=$(date "+%Y-%m-%d %H:%M:%S")
    echo ${time} >> tmp\/log\/vmstatlog_${1}
    vm_stat >> tmp\/log\/vmstatlog_${1}
    swapfile_count=$(ls /private/var/vm/swapfile* 2>/dev/null | wc -l)
    echo "Swapfile count: ${swapfile_count}" >> tmp/log/vmstatlog_${1}
}

function catfootprint
{
    footprint --swapped --wired -a -j tmp/log/footprint_${1}.json > /dev/null 2>&1

    # 文本采集方式
    # time=$(date "+%Y-%m-%d %H:%M:%S")
    # echo ${time} >> tmp\/log\/footprint_${1}
    # footprint --swapped --wired -a >> tmp\/log\/footprint_${1}

}

function catsysctl
{
    /var/jb/usr/sbin/sysctl vm.compressor_bytes_used >> tmp\/log\/sysctl_${1}
    /var/jb/usr/sbin/sysctl vm.compressor_compressed_bytes >> tmp\/log\/sysctl_${1}
    /var/jb/usr/sbin/sysctl vm.memory_pressure >> tmp\/log\/sysctl_${1}
    /var/jb/usr/sbin/sysctl vm.swapusage >> tmp\/log\/sysctl_${1}
}

function catzprint
{
    time=$(date "+%Y-%m-%d %H:%M:%S")
    echo ${time} >> tmp/log/zprint_${1}
    /var/jb/var/root/zprint_hack && zprint >> tmp/log/zprint_${1}
}

# shellcheck disable=SC2120
function catargs
{
    rm -rf tmp/log/
    mkdir tmp/log/
    i=1
    while true
    do
        catfootprint ${i}
        catzprint ${i}

        read -n 1 key
        # 回车触发

        sleep 10
        # 10s一触发

        i=$((i+1))
    done
    
    i=$((i+1))
    echo "end=================" >> tmp\/log\/footprint_${1}
}

catargs

