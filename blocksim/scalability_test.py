import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def memory_usage():
    # Memory usage in kB
    with open('/proc/self/status') as f:
        memusage = f.read().split('VmRSS:')[1].split('\n')[0][:-3]
    return int(memusage.strip())


def get_tx_num():
    x = []
    for i in range(1, 11):
        json_file = 'tx_count_' + str(i) + '000.json'

        path = Path.cwd() / 'DLASC' / 'simulator-master' / 'src' / json_file
        if not path.exists():
            raise Exception('Wrong working dir. Should be blocksim-dlasc')

        all_days = True
        with path.open() as f:
            all_days_tx = json.load(f)
            if all_days:
                node_tx = []
                for key, value in all_days_tx.items():
                    if int(key[-2:-1]) < 1:
                        node_tx.append(all_days_tx[key][1:])
                node_tx_array = np.array(node_tx)
                sum_tx = np.sum(node_tx_array, axis=0)

                print(np.sum(sum_tx[0:30]))
        x.append(np.sum(sum_tx[0:30]))
    return x


def plot_time(x):
    # x = np.logspace(0, 4, 5)
    # x = np.linspace(1000, 10000, num=10)

    y_sim = []
    y_run = []
    faulty_run = []
    faulty_sim = []
    for i in range(1, 11):
        json_file = 'tx_count_' + str(i) + '000.json'
        path_sim = Path.cwd() / 'blocksim' / 'output' / ('PBFT_simulated_time_' + json_file)
        path_run = Path.cwd() / 'blocksim' / 'output' / ('PBFT_running_time_' + json_file)

        # path_run_pbft = Path.cwd() / 'blocksim' / 'output' / ('PBFT_running_time_' + json_file)
        with path_sim.open() as f:
            y_sim.append(json.load(f))
        with path_run.open() as f:
            y_run.append(json.load(f))

        path_sim = Path.cwd() / 'blocksim' / 'output' / ('faulty_PBFT_simulated_time_' + json_file)
        path_run = Path.cwd() / 'blocksim' / 'output' / ('faulty_PBFT_running_time_' + json_file)

        # path_run_pbft = Path.cwd() / 'blocksim' / 'output' / ('PBFT_running_time_' + json_file)
        with path_sim.open() as f:
            faulty_sim.append(json.load(f))
        with path_run.open() as f:
            faulty_run.append(json.load(f))
        # with path_run_pbft.open() as f:
        #     pbft_run.append(json.load(f))

    ave_sim = [np.average(sim) for sim in y_sim]
    ave_run = [np.average(run) for run in y_run]

    faulty_sim = [np.average(sim) for sim in faulty_sim]
    faulty_run = [np.average(run) for run in faulty_run]

    # pbft_ave_run = [np.average(run) for run in pbft_run]

    std_sim = [np.std(sim) for sim in y_sim]
    std_run = [np.std(run) for run in y_run]

    # pbft_std_run = [np.std(run) for run in pbft_run]
    fig = plt.figure()
    plt.title("pBFT SImulation Example")
    # plt.errorbar(x, ave_run, yerr=std_run,
    #              label='Simulation Running Time')
    # plt.errorbar(x, ave_sim, yerr=std_sim,
    #              label='Simulated Time')

    plt.plot(x, ave_run,
                 label='Simulation Running Time')
    plt.plot(x, ave_sim,
                 label='Simulated Time')
    plt.plot(x, faulty_run, '--',
             label='Simulation Running Time with Faulty Leaders')
    plt.plot(x, faulty_sim, '--',
             label='Simulated Time with Faulty Leaders')

    # plt.errorbar(x, pbft_ave_run, yerr=pbft_std_run,
    #              label='PBFT running time')
    for i in range(len(x)):
        plt.text(x[i], ave_run[i]+2, "%d" % ave_run[i], ha="center")
        plt.text(x[i], faulty_run[i] + 2, "%d" % faulty_run[i], ha="center")
        # plt.text(x[i], pbft_ave_run[i]+2, "%d" % pbft_ave_run[i], ha="center")
        plt.text(x[i], ave_sim[i]-12, "%d" % ave_sim[i], ha="center")
        plt.text(x[i], faulty_sim[i] + 2, "%d" % faulty_sim[i], ha="center")
    plt.legend(loc='best')
    plt.xlabel('Number of Transactions')
    plt.ylabel('Time (seconds)')
    plt.savefig(Path.cwd() / 'blocksim' / 'output' / 'Time.png')
    plt.show()
    plt.close()


def plot_faulty():
    x = list(range(7))
    nBlock = [99, 85, 67, 61, 56, 46, 36]
    ncBlock = [99, 85, 67, 61, 56, 46, 4]
    nfBlock = [6, 4, 5, 8, 5, 4]
    fig = plt.figure()
    plt.title("Throughput of 16 pBFT Nodes versus Faulty Nodes")
    plt.ylabel('Average Number of Blocks in 100 Seconds')
    plt.xlabel('Number of Faulty Nodes (Whose 50% messages are dropped)')
    plt.plot(x[1::], nfBlock,
             label='Nubmer of Blocks of Faulty Nodes')
    plt.plot(x, nBlock,
             label='Nubmer of Blocks of Authorities')
    plt.plot(x, ncBlock,
             label='Nubmer of Blocks of Non-Authorities')
    plt.axvline(x=5.5, color='k', linestyle='--', label='Boundary of Consistency (f=5)')
    # plt.text(x[-1], ncBlock[-1] + 1, "%d" % ncBlock[-1], ha="center")
    for i in range(1, len(x)):
        plt.text(x[i], nfBlock[i-1]+1, "%d" % nfBlock[i-1], ha="center")
    for i in range(len(x)):
        plt.text(x[i], nBlock[i]+1, "%d" % nBlock[i], ha="center")
    plt.legend(loc='best')
    plt.show()


if __name__ == '__main__':
    # x = get_tx_num()
    # print(len(x))
    # plot_time(x)
    plot_faulty()
