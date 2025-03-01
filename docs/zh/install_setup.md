# 欢迎使用 PaddleScience

## 1. 开始安装

### 1.1 从 docker 镜像启动[可选]

如果你对 docker 有一定了解，则可以通过我们提供的 docker 文件，直接构建出能运行 PaddleScience 的环境。按照下列步骤构建 docker 并自动进入该环境，以运行 PaddleScience。

1. 下载 pymesh 预编译文件压缩包 [pymesh.tar.xz](https://paddle-org.bj.bcebos.com/paddlescience/docker/pymesh.tar.xz)，并放置在 `PaddleScience/docker/` 目录下
2. 执行 `bash run.sh`，等待 docker build 完毕后自动进入环境。如果出现因网络问题导致的 apt 下载报错，则重复执行 `bash run.sh` 直至 build 完成即可
3. 在 docker 环境中，执行 `ldconfig`

### 1.2 python 环境安装[可选]

如果你还没有 python 环境或者 python 版本小于 3.7，则推荐使用 Anaconda 安装并配置 python 环境，否则可以忽略本步骤

1. 根据系统环境，从 [https://repo.anaconda.com/archive/](https://repo.anaconda.com/archive/) 中下载对应的 Anaconda3 安装包，并手动安装
2. 创建 python 3.7 环境，并进入该环境

    ``` sh
    # 使用 conda 创建 python 环境，并命名为 "ppsci_py37"
    conda create -n ppsci_py37 python=3.7 # 3.8 也可以

    # 进入创建好的 "ppsci_py37" 环境
    conda activate ppsci_py37
    ```

### 1.3 安装 PaddlePaddle

请在 [PaddlePaddle](https://www.paddlepaddle.org.cn/install/quick?docurl=/documentation/docs/zh/develop/install/pip/linux-pip.html) 官网按照您的运行环境，安装 **develop** 版的 PaddlePaddle

### 1.4 安装 PaddleScience

从 [1.3.1 git 安装](#131-git) 和 [1.3.2 pip 安装](#132-pip) 任选一种安装方式即可

#### 1.4.2 git 安装

1. 执行以下命令，从 github 上克隆 PaddleScience 项目，进入 PaddleScience 目录，并将该目录添加到系统环境变量中

    ``` shell
    git clone https://github.com/PaddlePaddle/PaddleScience.git
    # 若 github clone 速度比较慢，可以使用 gitee clone
    # git clone https://gitee.com/paddlepaddle/PaddleScience.git

    cd PaddleScience
    git checkout release/1.1
    export PYTHONPATH=$PWD:$PYTHONPATH
    ```

2. 安装必要的依赖包

    ``` shell
    pip install -r requirements.txt
    ```

#### 1.4.3 pip 安装

执行以下命令进行 pip 安装

``` shell
pip install paddlesci
```

???+ Info "安装注意事项"

    如需使用外部导入STL文件来构建几何，以及使用加密采样等功能，还需额外安装四个依赖库：
    <li> [open3d](https://github.com/isl-org/Open3D/tree/master#python-quick-start)（推荐pip安装）</li>
    <li> pybind11（Python>=3.10 的用户安装 pysdf 前请先执行 `pip install -U pybind11`）</li>
    <li> [pysdf](https://github.com/sxyu/sdf)（推荐pip安装）</li>
    <li> [pymesh](https://pymesh.readthedocs.io/en/latest/installation.html#download-the-source)（推荐编译安装）</li>

## 2. 验证安装

执行以下代码，验证安装的 PaddleScience 基础功能是否正常

``` shell
python -c "import ppsci; ppsci.utils.run_check()"
```

如果出现 `PaddleScience is installed successfully.✨ 🍰 ✨`，则说明安装验证成功。

## 3. 开始使用

- 运行内置的案例（以 **ldc2d_unsteady_Re10.py** 为例）

    ``` shell
    cd examples/ldc/
    python ./ldc2d_unsteady_Re10.py
    ```

- 编写自己的案例（假设案例名为demo）

    推荐在 `examples/` 下新建 `demo` 文件夹，然后在 `demo` 文件夹下新建 `demo.py`，最后在 `demo.py` 文件中使用 PaddleScience 提供的 [API](./api/arch.md) 编写代码

    ``` py linenums="1" title="examples/demo/demo.py"
    import ppsci

    # write your code here...
    ```

    编写完毕后运行你的代码

    ``` shell
    cd examples/demo
    python ./demo.py
    ```
