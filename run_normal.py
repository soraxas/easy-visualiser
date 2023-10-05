import numpy as np

import easy_visualiser as ev

# viz = ev.gcv("pyro")
viz = ev.gcv("thread")

# viz = ev.Visualiser()


viz.scatter(np.random.rand(5, 3))
# while viz:
#     time.sleep(1)
#     viz
#     continue
#     viz.scatter(np.random.rand(5, 3))
#     print(viz)
#     print(bool(viz))


with viz.is_running():
    while viz:
        # time.sleep(1)
        # viz
        # continue
        viz.scatter(np.random.rand(5, 3))
        print(viz)
        print(bool(viz))

        viz.risent

        viz.spin_until_keypress()
