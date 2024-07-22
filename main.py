from generator import _gen_logger, _gen_process, _gen_preprocess_path
import logging

name = "P1135.gen"
copy = True

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    _gen_process(copy_to_clipboard=copy, path=_gen_preprocess_path(name))
    _gen_logger.info("Process completed.")
    exit(0)
