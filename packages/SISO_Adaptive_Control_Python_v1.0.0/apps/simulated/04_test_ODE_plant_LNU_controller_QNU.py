from physical_ode_test import run_physical_test
from project_setup import ctrl_lnu_qnu_eval_file, ctrl_lnu_qnu_file


if __name__ == "__main__":
    run_physical_test("LNU", "QNU", ctrl_lnu_qnu_file, ctrl_lnu_qnu_eval_file)
