from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import json


def plot_time():
    # x = np.logspace(0, 4, 5)
    x = np.linspace(1000, 10000, num=10)

    y_sim = []
    y_run = []
    # for i in range(5):
    #     tx_count = '{:.0f}'.format(x[i])
    for i in range(1, 11):
        json_file = 'tx_count_' + str(i) + '000.json'
        path_sim = Path.cwd() / 'blocksim' / 'output' / ('simulation_time_' + json_file)
        path_run = Path.cwd() / 'blocksim' / 'output' / ('running_time_' + json_file)
        with path_sim.open() as f:
            y_sim.append(json.load(f))
        with path_run.open() as f:
            y_run.append(json.load(f))
    # print(y_run)
    ave_sim = [np.average(sim) for sim in y_sim]
    ave_run = [np.average(run) for run in y_run]

    std_sim = [np.std(sim) for sim in y_sim]
    std_run = [np.std(run) for run in y_run]
    # print(ave_sim, ave_run)
    fig = plt.figure()
    plt.errorbar(x, ave_run, yerr=std_run,
                 label='run time')
    plt.errorbar(x, ave_sim, yerr=std_sim,
                 label='sim time')
    for i in range(len(x)):
        plt.text(x[i], ave_run[i]+2, "%d" % ave_run[i], ha="center")
        plt.text(x[i], ave_sim[i]+2, "%d" % ave_sim[i], ha="center")
    # plt.xscale('log')
    # plt.yscale('log')
    plt.legend(loc='lower right')
    plt.savefig(Path.cwd() / 'blocksim' / 'output' / 'time.png')
    plt.show()
    plt.close()


if __name__ == '__main__':
    plot_time()
