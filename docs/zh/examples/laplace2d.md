# 2D-Laplace

<a href="https://aistudio.baidu.com/aistudio/projectdetail/6169897?sUid=455441&shared=1&ts=1684122038217" class="md-button md-button--primary" style>AI Studio快速体验</a>

## 1. 问题简介

2D-Laplace，在本文中代表拉普拉斯方程的2维形式。拉普拉斯方程因为由法国数学家拉普拉斯首先提出而得名。求解拉普拉斯方程是电磁学、天文学和流体力学等领域经常遇到的一类重要的数学问题，因为这种方程以势函数的形式描写了电场、引力场和流场等物理对象（一般统称为“保守场”或“有势场”）的性质。

## 2. 问题定义

拉普拉斯方程（2维形式）：

$$
\dfrac{\partial^{2} u}{\partial x^{2}} + \dfrac{\partial^{2} u}{\partial y^{2}} = 0, x \in (0, 1), y \in (0, 1)
$$

## 3. 问题求解

接下来开始讲解如何将问题一步一步地转化为 PaddleScience 代码，用深度学习的方法求解该问题。
为了快速理解 PaddleScience，接下来仅对模型构建、方程构建、计算域构建等关键步骤进行阐述，而其余细节请参考 [API文档](../api/arch.md)。

### 3.1 模型构建

在 2D-Laplace 问题中，每一个已知的坐标点 $(x, y)$ 都有对应的待求解的未知量 $u$
，我们在这里使用比较简单的 MLP(Multilayer Perceptron, 多层感知机) 来表示 $(x, y)$ 到 $(u)$ 的映射函数 $f: \mathbb{R}^2 \to \mathbb{R}^1$ ，即：

$$
u = f(x, y)
$$

上式中 $f$ 即为 MLP 模型本身，用 PaddleScience 代码表示如下

``` py linenums="35"
--8<--
examples/laplace/laplace2d.py:35:36
--8<--
```

为了在计算时，准确快速地访问具体变量的值，我们在这里指定网络模型的输入变量名是 `("x", "y")`，输出变量名是 `("u",)`，这些命名与后续代码保持一致。

接着通过指定 MLP 的层数、神经元个数，我们就实例化出了一个拥有 5 层隐藏神经元，每层神经元数为 20 的神经网络模型 `model`。

### 3.2 方程构建

由于 2D-Laplace 使用的是 Laplace 方程的2维形式，因此可以直接使用 PaddleScience 内置的 `Laplace`，指定该类的参数 `dim` 为2。

``` py linenums="38"
--8<--
examples/laplace/laplace2d.py:38:39
--8<--
```

### 3.3 计算域构建

本文中 2D Laplace 问题作用在以 (0.0, 0.0),  (1.0, 1.0) 为对角线的二维矩形区域，
因此可以直接使用 PaddleScience 内置的空间几何 `Rectangle` 作为计算域。

``` py linenums="41"
--8<--
examples/laplace/laplace2d.py:41:42
--8<--
```

### 3.4 约束构建

在本案例中，我们使用了两个约束条件在计算域中指导模型的训练分别是作用于采样点上的 Laplace 方程约束和作用于边界点上的约束。

在定义约束之前，需要给每一种约束指定采样点个数，表示每一种约束在其对应计算域内采样数据的数量，以及通用的采样配置。

``` py linenums="56"
--8<--
examples/laplace/laplace2d.py:56:58
--8<--
```

#### 3.4.1 内部点约束

以作用在内部点上的 `InteriorConstraint` 为例，代码如下：

``` py linenums="61"
--8<--
examples/laplace/laplace2d.py:61:69
--8<--
```

`InteriorConstraint` 的第一个参数是方程表达式，用于描述如何计算约束目标，此处填入在 [3.2 方程构建](#32) 章节中实例化好的 `equation["laplace"].equations`；

第二个参数是约束变量的目标值，在本问题中我们希望 Laplace 方程产生的结果 `laplace` 被优化至 0，因此将它的目标值全设为 0；

第三个参数是约束方程作用的计算域，此处填入在 [3.3 计算域构建](#33) 章节实例化好的 `geom["rect"]` 即可；

第四个参数是在计算域上的采样配置，此处我们使用全量数据点训练，因此 `dataset` 字段设置为 "IterableNamedArrayDataset" 且 `iters_per_epoch` 也设置为 1，采样点数 `batch_size` 设为 10201(表示99x99的等间隔网格加400个边界点)；

第五个参数是损失函数，此处我们选用常用的MSE函数，且 `reduction` 设置为 `"sum"`，即我们会将参与计算的所有数据点产生的损失项求和；

第六个参数是选择是否在计算域上进行等间隔采样，此处我们选择开启等间隔采样，这样能让训练点均匀分布在计算域上，有利于训练收敛；

第七个参数是约束条件的名字，我们需要给每一个约束条件命名，方便后续对其索引。此处我们命名为 "EQ" 即可。

#### 3.4.2 边界约束

同理，我们还需要构建矩形的四个边界的约束。但与构建 `InteriorConstraint` 约束不同的是，由于作用区域是边界，因此我们使用 `BoundaryConstraint` 类，代码如下：

``` py linenums="70"
--8<--
examples/laplace/laplace2d.py:70:77
--8<--
```

`BoundaryConstraint` 类第一个参数表示我们直接对网络模型的输出结果 `out["u"]` 作为程序运行时的约束对象；

第二个参数是指我们约束对象的真值如何获得，这里我们直接通过其解析解进行计算，定义解析解的代码如下：

``` py linenums="44"
--8<--
examples/laplace/laplace2d.py:44:48
--8<--
```

`BoundaryConstraint` 类其他参数的含义与 `InteriorConstraint` 基本一致，这里不再介绍。

### 3.5 超参数设定

接下来我们需要指定训练轮数和学习率，此处我们按实验经验，使用两万轮训练轮数，评估间隔为两百轮。

``` py linenums="26"
--8<--
examples/laplace/laplace2d.py:26:29
--8<--
```

### 3.6 优化器构建

训练过程会调用优化器来更新模型参数，此处选择较为常用的 `Adam` 优化器。

``` py linenums="84"
--8<--
examples/laplace/laplace2d.py:84:85
--8<--
```

### 3.7 评估器构建

在训练过程中通常会按一定轮数间隔，用验证集（测试集）评估当前模型的训练情况，因此使用 `ppsci.validate.GeometryValidator` 构建评估器。

``` py linenums="87"
--8<--
examples/laplace/laplace2d.py:87:102
--8<--
```

### 3.8 可视化器构建

在模型评估时，如果评估结果是可以可视化的数据，我们可以选择合适的可视化器来对输出结果进行可视化。

本文中的输出数据是一个区域内的二维点集，因此我们只需要将评估的输出数据保存成 **vtu格式** 文件，最后用可视化软件打开查看即可。代码如下：

``` py linenums="104"
--8<--
examples/laplace/laplace2d.py:104:113
--8<--
```

### 3.9 模型训练、评估与可视化

完成上述设置之后，只需要将上述实例化的对象按顺序传递给 `ppsci.solver.Solver`，然后启动训练、评估、可视化。

``` py linenums="115"
--8<--
examples/laplace/laplace2d.py:115:
--8<--
```

## 4. 完整代码

``` py linenums="1" title="laplace2d.py"
--8<--
examples/laplace/laplace2d.py
--8<--
```

## 5. 结果展示

<figure markdown>
  ![laplace 2d](../../images/laplace2d/laplace2d.png){ loading=lazy }
  <figcaption>模型预测结果</figcaption>
</figure>
