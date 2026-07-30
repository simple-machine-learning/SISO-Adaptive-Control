from physical_ode_test import run_physical_test
from project_setup import ctrl_lnu_lnu_eval_file, ctrl_lnu_lnu_file


if __name__ == "__main__":
    run_physical_test("LNU", "LNU", ctrl_lnu_lnu_file, ctrl_lnu_lnu_eval_file)
