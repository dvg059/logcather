import logging
# logging.basicConfig(filename='thrd.log', level=logging.DEBUG,
                    # format='(%(threadName)-9s) %(message)s',)


#logging.basicConfig(level=logging.WARNING,
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(threadName)-12s %(levelname)-8s %(message)s',
#                    datefmt='%m-%d %H:%M',
                    filename='signia_transfer_program.log',
                    filemode='w')