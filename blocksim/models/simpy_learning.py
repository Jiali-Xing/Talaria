import simpy


def car(env):
    flag = True
    while True:
        print('Start parking at %d' % env.now)
        parking_duration = 5
        yield env.timeout(parking_duration)
        print('Start driving at %d' % env.now)
        trip_duration = 2
        yield env.timeout(trip_duration)

        print('now=%d, car need to wait for some time, value=%d' % (env.now, 3))
        event = simpy.events.Timeout(env, delay=3, value=3)
        value = yield event
        print('now=%d, finish waiting, this happens in main time line' % env.now)

        if flag:
            env.process(traffic(env))
            # flag = False


def traffic(env):
    print('now=%d, this happens in parallel universe' % env.now)
    event = simpy.events.Timeout(env, delay=1, value=1)
    value = yield event
    print('now=%d, and does not interfere with main time line\'s car, value=%d' % (env.now, value))


if __name__ == '__main__':
    env = simpy.Environment()
    env.process(car(env))
    env.run(until=50)

