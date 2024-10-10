
# onboarding fresh

## 1. **Project Scope and Objectives**

The goals of the bluesky at i22 project is to prove in an experimental conditions that the [PANDA](https://github.com/PandABlocks) device. That is from the view of the future full replacement of the Time Frame Generator (TFG) and Zebra devices with the Panda device. This is just another migration away from legacy hardware. It is not the highest organizational priority at the moment.

At some point in the last 2-3 years Panda software achieved maturity and now it's only in a slow development phase, while the accent is put on using it in practice.
After proving the Panda device, the next phase will be a broader adotption of it.
At the moment of writing, there is around 20 those devices - they are not globally listed - around various beamlines, up to 5 on one.

At i22 specifically, there is one Panda. The i22-panda-testing project has three phases, each corresponding to a different experiment. The linkam experiment (where linkam is a temperature controller device), stopflow experiment (where a capillary tube with a chemical solution is under beam), and finally a pressure jump experiment (using a 'pressure cell', a custom sample environment device ). Each of those has more details in their python files in this repository.
Linkam was done in Fall 2023, Stopflow in June 2024, Pressure Jump is scheduled for March 2025.

The immediate goals of bluesky at i22 is to support the capability to run the two already tested experiment, and deliver the solution to run the third type by March.

## 2. **Team Structure and Roles**

The developers of the bluesky i22 project can be found in the [github repo](https://github.com/PandABlocks/PandABlocks-server).
Prior work has been done by Core DAQ developers.
Beamline scientists can be contacted for experiment goals.
Pressure cell is also used at i15 - this causes limited availablity.

Introduction to the Controls team in the Condense Matter science group is also necessary.

## 3. **Development Processes and Workflows**

There are no formal sprints here. [Blueapi](https://github.com/DiamondLightSource/blueapi) is used for running the experiments. Issues, pull requests are all sorted on github in this repo.
We have an existing test suite in place, and adding new tests resembling the existing ones will be necessary to make any new changes pass CI as there is a percentage code coverage requirement.

For an overview of the tools we use best review `pyproject.toml` and the `github workflows`.

## 4. **Technical Overview**

The blueapi is a REST service to run plans. It lives in a beamline-specific Kubernetes cluster, which manages the service. The service is configured to read configuration-as-code from the filesystem through the [scratch directory](https://dev-portal.diamond.ac.uk/guide/athena/how-tos/machine-day-testing/#downloading-repositories-into-the-mounted-scratch-directory). That way rapid testing of plans and devices is possible.

We write the plans and devices in async Python, and blueapi is a FastAPI application, which is under development.

## 5. **Risks and Mitigation Strategies**

The notes from the past experiments using PressureCell are on [Confluence](https://confluence.diamond.ac.uk/display/~qan22331/Pressure+Cell+Usage), however they need translating into our circumstances.
The plans that were ran in the past might suffer from [code rot](https://en.wikipedia.org/wiki/Software_rot) through changing dependencies.
The toolchain is long and complex, and subject to international collaboration and misunderstandings. Other facilities use the libraries in a slightly different way and some upstream changes that appeared compatible at times prove to break something downstream.

## 6. **Documentation and Resources**

- blueapi deployment <https://dev-portal.diamond.ac.uk/guide/athena/how-tos/machine-day-testing/>
- i22 blueapi instance <https://i22-blueapi.diamond.ac.uk/>
- kuberenetes cluster and namespace (might need asking the cloud team to give permissions) <https://k8s-i22-dashboard.diamond.ac.uk/#/workloads?namespace=i22-beamline>
- i22 beamline file in dodal <https://github.com/DiamondLightSource/dodal/blob/main/src/dodal/beamlines/i22.py>
- i22 specific devices in dodal <https://github.com/DiamondLightSource/dodal/tree/main/src/dodal/devices/i22>

useful extensions:

- bierner.markdown-mermaid
- charliermarsh.ruff
- davidanson.vscode-markdownlint
- eamodio.gitlens
- esbenp.prettier-vscode
- foxundermoon.shell-format
- github.copilot
- github.copilot-chat
- ms-azuretools.vscode-docker
- ms-pyright.pyright
- ms-python.debugpy
- ms-python.python
- ms-python.vscode-pylance
- ms-toolsai.jupyter
- ms-toolsai.jupyter-keymap
- ms-toolsai.jupyter-renderers
- ms-toolsai.vscode-jupyter-cell-tags
- ms-toolsai.vscode-jupyter-slideshow
- naumovs.color-highlight
- p1c2u.docker-compose
- redhat.vscode-yaml
- tamasfe.even-better-toml

## 7. **Metrics and Monitoring**

The main metric we use is 'does the plan work in testing on a machine day' when there are no users. This testing might also happen during *comissioning time* at the beamline, that is after a shutdown period yet before the users arrive. Some, though at times only partial, beam is available then.

We use kuberentes admin dashboard to track the reliability of our software

## 8. **Communication Channels**

The beamline scientists use email and often teams over Slack.
Developers use primarily Slack, many exchanges are better documented though if they happen in a github issue (use case and planning) or a Pull Request (discussion of the implementation).
The Panda meetings are usually every two weeks on a Tuesday afternoon.
We aim to do machine day testing every week.

The plan for all of this might become more Agile, but that is pending some things to happen on a nebulous timeline.

## 9. **Future Vision**

At the moment there is a couple of issues open.
We aim to write out more comprehensive testing for the existing plans, as well as for the devices.
i15 collaboration might be in order to achieve more reliability with the pressure cell.
Finally the PressureJump experiment plan is underspecified at the moment - further requirements should be gathered.
