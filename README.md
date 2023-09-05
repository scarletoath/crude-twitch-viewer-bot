# Crude Twitch Viewer Bot (CTVBot)
[![](https://img.shields.io/github/downloads/scarletoath/crude-twitch-viewer-bot/total)](https://github.com/scarletoath/crude-twitch-viewer-bot/releases/latest)
[![](https://github.com/scarletoath/crude-twitch-viewer-bot/actions/workflows/pytest.yml/badge.svg)](https://github.com/scarletoath/crude-twitch-viewer-bot/actions/workflows/pytest.yml)
[![format & lint](https://github.com/scarletoath/crude-twitch-viewer-bot/actions/workflows/format_lint.yml/badge.svg)](https://github.com/scarletoath/crude-twitch-viewer-bot/actions/workflows/format_lint.yml)
[![](https://github.com/scarletoath/crude-twitch-viewer-bot/actions/workflows/build.yml/badge.svg)](https://github.com/scarletoath/crude-twitch-viewer-bot/actions/workflows/build.yml)

>Disclaimer: For educational purpose only. Any discussion of illegal use will be deleted immediately!

![image](https://github.com/scarletoath/crude-twitch-viewer-bot/assets/1894141/812ef4bf-0267-46b8-b39f-bad2f048943b)
### Additions / Changes / Fixes to source repo
- Tooltip hover
- Updated layout with editable counts
- Auto-save settings (with advanced configuration)
- Auto-spawn until target count
- More colors for statuses
- Quick manual restart

### Getting Started
Download the one-file executable for Windows, Linux and MacOS from the [latest CTVBot release](https://github.com/jlplenio/crude-twitch-viewer-bot/releases/latest).  
Read the comprehensive [wiki](https://github.com/jlplenio/crude-twitch-viewer-bot/wiki) for a [detailed tutorial](https://github.com/jlplenio/crude-twitch-viewer-bot/wiki/Detailed-Tutorial), [usage tips](https://github.com/jlplenio/crude-twitch-viewer-bot/wiki/Advanced-features-and-controls) and [troubleshooting steps](https://github.com/jlplenio/crude-twitch-viewer-bot/wiki/Troubleshooting).

[:coffee: Sponsor me a coffee](https://ko-fi.com/jlplenio) or become a :gem: [Supporter & Feature Tester](https://ko-fi.com/jlplenio/tiers) to support the development. 

### Mandatory Requirements
- You need to provide your own private HTTP proxies to the [proxy_list.txt](proxy/proxy_list.txt)  
  Buy trusted proxies [here](https://www.webshare.io/?referral_code=w6nfvip4qp3g) or follow the [Webshare.io Proxies Guide](https://github.com/jlplenio/crude-twitch-viewer-bot/wiki/Webshare.io-Proxies-Guide).
- Chrome needs to be already installed on your system.

### Platform Support Overview

| Platform              |                  Twitch                   |      Youtube       |   Kick    |
|-----------------------|:-----------------------------------------:|:------------------:|:---------:|
| General Functionality |            :heavy_check_mark:             | :heavy_check_mark: | :warning: |
| Lowest Quality Select |            :heavy_check_mark:             | :heavy_check_mark: |    :heavy_check_mark:    |
| Status Boxes Updates  |            :heavy_check_mark:             | :heavy_check_mark: |    :x:    |
| Login/Authentication  | ⏳[:gem:](https://github.com/jlplenio/crude-twitch-viewer-bot/discussions/categories/supporter-feature-tester) |        :x:         |    :x:    |
| Automatic Follow | ⏳[:gem:](https://github.com/jlplenio/crude-twitch-viewer-bot/discussions/categories/supporter-feature-tester)  |        :x:         |    :x:    |
| Automatic Chat | ⏳ |        :x:         |    :x:    |

:heavy_check_mark: Supported, :warning: Problems, :x: Unsupported, ⏳ In Development, [:gem: Preview Available](https://github.com/jlplenio/crude-twitch-viewer-bot/discussions/categories/supporter-feature-tester) 

### In Action

![](docs/gui.png)

#### Controls and Color codes of the square boxes

⬛ - Instance is spawned.    🟨 - Instance is buffering.    🟩 - Instance is actively watching.

🖱️ Left click: Refresh page.
🖱️ Right click: Destroy instance.
🖱️ Left click + CTRL: Take screenshot.

### Misc
- CPU load and bandwidth can get heavy. Channels with 160p work best.
- Tested on Windows 10 with headless ~100, headful ~30. Linux and macOS is experimental.

The Crude Twitch Viewer Bot (CTVBot) is a small GUI tool that spawns muted Google Chrome instances via [Playwright](https://github.com/microsoft/playwright-python), each with a different user-agent and HTTP proxy connection. Each instance navigates to the streaming channel and selects the lowest possible resolution.

Read the comprehensive [wiki](https://github.com/jlplenio/crude-twitch-viewer-bot/wiki) for a [detailed tutorial](https://github.com/jlplenio/crude-twitch-viewer-bot/wiki/Detailed-Tutorial), [usage tips](https://github.com/jlplenio/crude-twitch-viewer-bot/wiki/Advanced-features-and-controls) and [troubleshooting steps](https://github.com/jlplenio/crude-twitch-viewer-bot/wiki/Troubleshooting).





