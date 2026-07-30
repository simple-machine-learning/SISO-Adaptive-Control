from physical_ode_test import run_physical_test
from project_setup import ctrl_qnu_lnu_eval_file, ctrl_qnu_lnu_file


if __name__ == "__main__":
    run_physical_test("QNU", "LNU", ctrl_qnu_lnu_file, ctrl_qnu_lnu_eval_file)
