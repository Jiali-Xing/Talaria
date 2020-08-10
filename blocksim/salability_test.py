from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import json


def memory_usage():
    # Memory usage in kB
    with open('/proc/self/status') as f:
        memusage = f.read().split('VmRSS:')[1].split('\n')[0][:-3]
    return int(memusage.strip())


def plot_time():
    # x = np.logspace(0, 4, 5)
    x = np.linspace(1000, 10000, num=10)

    y_sim = []
    y_run = []
    pbft_run = []
    for i in range(1, 11):
        json_file = 'tx_count_' + str(i) + '000.json'
        path_sim = Path.cwd() / 'blocksim' / 'output' / ('PoA_simulated_time_' + json_file)
        path_run = Path.cwd() / 'blocksim' / 'output' / ('PoA_running_time_' + json_file)

        path_run_pbft = Path.cwd() / 'blocksim' / 'output' / ('PBFT_running_time_' + json_file)
        with path_sim.open() as f:
            y_sim.append(json.load(f))
        with path_run.open() as f:
            y_run.append(json.load(f))

        with path_run_pbft.open() as f:
            pbft_run.append(json.load(f))

    ave_sim = [np.average(sim) for sim in y_sim]
    ave_run = [np.average(run) for run in y_run]

    pbft_ave_run = [np.average(run) for run in pbft_run]

    std_sim = [np.std(sim) for sim in y_sim]
    std_run = [np.std(run) for run in y_run]

    pbft_std_run = [np.std(run) for run in pbft_run]
    fig = plt.figure()
    plt.errorbar(x, ave_run, yerr=std_run,
                 label='PoA running time')
    plt.errorbar(x, ave_sim, yerr=std_sim,
                 label='simulated time')

    plt.errorbar(x, pbft_ave_run, yerr=pbft_std_run,
                 label='PBFT running time')
    for i in range(len(x)):
        plt.text(x[i], ave_run[i]+2, "%d" % ave_run[i], ha="center")
        plt.text(x[i], pbft_ave_run[i]+2, "%d" % pbft_ave_run[i], ha="center")
        plt.text(x[i], ave_sim[i]+2, "%d" % ave_sim[i], ha="center")
    plt.legend(loc='upper left')
    plt.xlabel('Number of orders per day')
    plt.ylabel('Time (seconds)')
    plt.savefig(Path.cwd() / 'blocksim' / 'output' / 'Time.png')
    plt.show()
    plt.close()


if __name__ == '__main__':
    plot_time()
