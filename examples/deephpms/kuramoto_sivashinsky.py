# Copyright (c) 2023 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import paddle
import paddle.nn.functional as F

import ppsci
from ppsci.autodiff import hessian
from ppsci.autodiff import jacobian
from ppsci.utils import config
from ppsci.utils import logger


def pde_loss_func(output_dict, *args):
    losses = F.mse_loss(output_dict["f_pde"], output_dict["du_t"], "sum")
    return losses


def pde_l2_rel_func(output_dict, *args):
    rel_l2 = paddle.norm(output_dict["du_t"] - output_dict["f_pde"]) / paddle.norm(
        output_dict["du_t"]
    )
    metric_dict = {"f_pde": rel_l2}
    return metric_dict


def boundary_loss_func(output_dict, *args):
    u_b = output_dict["u_idn"]
    u_lb, u_ub = paddle.split(u_b, 2, axis=0)

    x_b = output_dict["x"]
    du_x = jacobian(u_b, x_b)
    du_xx = hessian(u_b, x_b)
    du_xxx = jacobian(du_xx, x_b)

    du_x_lb, du_x_ub = paddle.split(du_x, 2, axis=0)
    du_xx_lb, du_xx_ub = paddle.split(du_xx, 2, axis=0)
    du_xxx_lb, du_xxx_ub = paddle.split(du_xxx, 2, axis=0)

    losses = F.mse_loss(u_lb, u_ub, "sum")
    losses += F.mse_loss(du_x_lb, du_x_ub, "sum")
    losses += F.mse_loss(du_xx_lb, du_xx_ub, "sum")
    losses += F.mse_loss(du_xxx_lb, du_xxx_ub, "sum")
    return losses


if __name__ == "__main__":
    # open FLAG for higher order differential operator when order >= 4
    paddle.fluid.core.set_prim_eager_enabled(True)

    args = config.parse_args()
    ppsci.utils.misc.set_random_seed(42)
    DATASET_PATH = "./datasets/DeepHPMs/KS.mat"
    DATASET_PATH_SOL = "./datasets/DeepHPMs/KS.mat"
    OUTPUT_DIR = "./output_ks/" if args.output_dir is None else args.output_dir

    # initialize logger
    logger.init_logger("ppsci", f"{OUTPUT_DIR}/train.log", "info")

    # initialize burgers boundaries
    t_lb = paddle.to_tensor([0.0])
    t_ub = paddle.to_tensor([50.0])
    x_lb = paddle.to_tensor([-10.0])
    x_ub = paddle.to_tensor([10.0])

    # boundaries of KS_chaotic.mat
    # t_lb = paddle.to_tensor([0.0])
    # t_ub = paddle.to_tensor([100.0])
    # x_lb = paddle.to_tensor([0.0])
    # x_ub = paddle.to_tensor([32.0 * np.pi])

    # initialize models
    model_idn = ppsci.arch.MLP(("t", "x"), ("u_idn",), 4, 50, "sin")
    model_pde = ppsci.arch.MLP(
        ("u_x", "du_x", "du_xx", "du_xxx", "du_xxxx"),
        ("f_pde",),
        2,
        100,
        "sin",
    )

    # initialize transform
    def transform_u(_in):
        t, x = _in["t"], _in["x"]
        t = 2.0 * (t - t_lb) * paddle.pow((t_ub - t_lb), -1) - 1.0
        x = 2.0 * (x - x_lb) * paddle.pow((x_ub - x_lb), -1) - 1.0
        input_trans = {"t": t, "x": x}
        return input_trans

    def transform_f(input, model, out_key):
        in_idn = {"t": input["t"], "x": input["x"]}
        x = input["x"]
        u = model(in_idn)[out_key]
        du_x = jacobian(u, x)
        du_xx = hessian(u, x)
        du_xxx = jacobian(du_xx, x)
        du_xxxx = hessian(du_xx, x)
        input_trans = {
            "u_x": u,
            "du_x": du_x,
            "du_xx": du_xx,
            "du_xxx": du_xxx,
            "du_xxxx": du_xxxx,
        }
        return input_trans

    def transform_f_idn(_in):
        return transform_f(_in, model_idn, "u_idn")

    # register transform
    model_idn.register_input_transform(transform_u)
    model_pde.register_input_transform(transform_f_idn)

    # initialize model list
    model_list = ppsci.arch.ModelList((model_idn, model_pde))

    # set training hyper-parameters
    ITERS_PER_EPOCH = 1
    EPOCHS = 50000 if args.epochs is None else args.epochs  # set 1 for LBFGS
    # MAX_ITER = 50000  # for LBFGS

    # initialize optimizer
    # Adam
    optimizer_idn = ppsci.optimizer.Adam(1e-4)((model_idn,))
    optimizer_pde = ppsci.optimizer.Adam(1e-4)((model_pde,))

    # LBFGS
    # optimizer_idn = ppsci.optimizer.LBFGS(max_iter=MAX_ITER)((model_idn, ))
    # optimizer_pde = ppsci.optimizer.LBFGS(max_iter=MAX_ITER)((model_pde, ))

    # stage 1: training identification net
    # manually build constraint(s)
    train_dataloader_cfg_idn = {
        "dataset": {
            "name": "IterableMatDataset",
            "file_path": DATASET_PATH,
            "input_keys": ("t", "x"),
            "label_keys": ("u_idn",),
            "alias_dict": {"t": "t_train", "x": "x_train", "u_idn": "u_train"},
        },
    }

    sup_constraint_idn = ppsci.constraint.SupervisedConstraint(
        train_dataloader_cfg_idn,
        ppsci.loss.MSELoss("sum"),
        {"u_idn": lambda out: out["u_idn"]},
        name="u_mse_sup",
    )
    constraint_idn = {sup_constraint_idn.name: sup_constraint_idn}

    # manually build validator
    eval_dataloader_cfg_idn = {
        "dataset": {
            "name": "IterableMatDataset",
            "file_path": DATASET_PATH,
            "input_keys": ("t", "x"),
            "label_keys": ("u_idn",),
            "alias_dict": {"t": "t_star", "x": "x_star", "u_idn": "u_star"},
        },
    }

    sup_validator_idn = ppsci.validate.SupervisedValidator(
        train_dataloader_cfg_idn,
        ppsci.loss.MSELoss("sum"),
        {"u_idn": lambda out: out["u_idn"]},
        {"l2": ppsci.metric.L2Rel()},
        name="u_L2_sup",
    )
    validator_idn = {sup_validator_idn.name: sup_validator_idn}

    # initialize solver
    solver = ppsci.solver.Solver(
        model_list,
        constraint_idn,
        OUTPUT_DIR,
        optimizer_idn,
        None,
        EPOCHS,
        ITERS_PER_EPOCH,
        eval_during_train=False,
        validator=validator_idn,
    )

    # train model
    solver.train()
    # evaluate after finished training
    solver.eval()

    # stage 2: training pde net
    # manually build constraint(s)
    train_dataloader_cfg_pde = {
        "dataset": {
            "name": "IterableMatDataset",
            "file_path": DATASET_PATH,
            "input_keys": ("t", "x"),
            "label_keys": ("du_t",),
            "alias_dict": {"t": "t_train", "x": "x_train", "du_t": "t_train"},
        },
    }

    sup_constraint_pde = ppsci.constraint.SupervisedConstraint(
        train_dataloader_cfg_pde,
        ppsci.loss.FunctionalLoss(pde_loss_func),
        {
            "du_t": lambda out: jacobian(out["u_idn"], out["t"]),
            "f_pde": lambda out: out["f_pde"],
        },
        name="f_mse_sup",
    )
    constraint_pde = {sup_constraint_pde.name: sup_constraint_pde}

    # manually build validator
    eval_dataloader_cfg_pde = {
        "dataset": {
            "name": "IterableMatDataset",
            "file_path": DATASET_PATH,
            "input_keys": ("t", "x"),
            "label_keys": ("du_t",),
            "alias_dict": {"t": "t_star", "x": "x_star", "du_t": "t_star"},
        },
    }

    sup_validator_pde = ppsci.validate.SupervisedValidator(
        eval_dataloader_cfg_pde,
        ppsci.loss.FunctionalLoss(pde_loss_func),
        {
            "du_t": lambda out: jacobian(out["u_idn"], out["t"]),
            "f_pde": lambda out: out["f_pde"],
        },
        {"l2": ppsci.metric.FunctionalMetric(pde_l2_rel_func)},
        name="f_L2_sup",
    )
    validator_pde = {sup_validator_pde.name: sup_validator_pde}

    # update solver
    solver = ppsci.solver.Solver(
        model_list,
        constraint_pde,
        OUTPUT_DIR,
        optimizer_pde,
        None,
        EPOCHS,
        ITERS_PER_EPOCH,
        eval_during_train=False,
        validator=validator_pde,
    )

    # train model
    solver.train()
    # evaluate after finished training
    solver.eval()

    # stage 3: training solution net, reuse identification net
    # manually build constraint(s)
    train_dataloader_cfg_sol_f = {
        "dataset": {
            "name": "IterableMatDataset",
            "file_path": DATASET_PATH_SOL,
            "input_keys": ("t", "x"),
            "label_keys": ("du_t",),
            "alias_dict": {"t": "t_f_train", "x": "x_f_train", "du_t": "t_f_train"},
        },
    }
    train_dataloader_cfg_sol_init = {
        "dataset": {
            "name": "IterableMatDataset",
            "file_path": DATASET_PATH_SOL,
            "input_keys": ("t", "x"),
            "label_keys": ("u_idn",),
            "alias_dict": {"t": "t0", "x": "x0", "u_idn": "u0"},
        },
    }
    train_dataloader_cfg_sol_bc = {
        "dataset": {
            "name": "IterableMatDataset",
            "file_path": DATASET_PATH_SOL,
            "input_keys": ("t", "x"),
            "label_keys": ("x",),
            "alias_dict": {"t": "tb", "x": "xb"},
        },
    }

    sup_constraint_sol_f = ppsci.constraint.SupervisedConstraint(
        train_dataloader_cfg_sol_f,
        ppsci.loss.FunctionalLoss(pde_loss_func),
        {
            "f_pde": lambda out: out["f_pde"],
            "du_t": lambda out: jacobian(out["u_idn"], out["t"]),
        },
        name="f_mse_sup",
    )
    sup_constraint_sol_init = ppsci.constraint.SupervisedConstraint(
        train_dataloader_cfg_sol_init,
        ppsci.loss.MSELoss("sum"),
        {"u_idn": lambda out: out["u_idn"]},
        name="u0_mse_sup",
    )
    sup_constraint_sol_bc = ppsci.constraint.SupervisedConstraint(
        train_dataloader_cfg_sol_bc,
        ppsci.loss.FunctionalLoss(boundary_loss_func),
        {
            "x": lambda out: out["x"],
            "u_idn": lambda out: out["u_idn"],
        },
        name="ub_mse_sup",
    )
    constraint_sol = {
        sup_constraint_sol_f.name: sup_constraint_sol_f,
        sup_constraint_sol_init.name: sup_constraint_sol_init,
        sup_constraint_sol_bc.name: sup_constraint_sol_bc,
    }

    # manually build validator
    eval_dataloader_cfg_sol = {
        "dataset": {
            "name": "IterableMatDataset",
            "file_path": DATASET_PATH_SOL,
            "input_keys": ("t", "x"),
            "label_keys": ("u_idn",),
            "alias_dict": {"t": "t_star", "x": "x_star", "u_idn": "u_star"},
        },
    }

    sup_validator_sol = ppsci.validate.SupervisedValidator(
        eval_dataloader_cfg_sol,
        ppsci.loss.MSELoss("sum"),
        {"u_idn": lambda out: out["u_idn"]},
        {"l2": ppsci.metric.L2Rel()},
        name="u_L2_sup",
    )
    validator_sol = {
        sup_validator_sol.name: sup_validator_sol,
    }

    # update solver
    solver = ppsci.solver.Solver(
        model_list,
        constraint_sol,
        OUTPUT_DIR,
        optimizer_idn,
        None,
        EPOCHS,
        ITERS_PER_EPOCH,
        eval_during_train=False,
        validator=validator_sol,
    )

    # train model
    solver.train()
    # evaluate after finished training
    solver.eval()
