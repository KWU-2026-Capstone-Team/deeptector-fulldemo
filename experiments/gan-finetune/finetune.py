"""Light fine-tune of ONE original spatial model (ConvNeXt fold 1) on StyleGAN vs FFHQ faces.

Only the last ConvNeXt stage + the head are trained (early layers frozen) with a small LR,
to add StyleGAN sensitivity while limiting forgetting of the FF++ face-swap skill.
Output keeps the original checkpoint format so it could later replace a fold file.
"""
from __future__ import annotations

import argparse
import json
import random
import time

import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

from common import CKPT, SEED, infer, list_split, load_classifier, original_checkpoints

AUG = transforms.Compose([
    transforms.RandomResizedCrop(224, scale=(0.85, 1.0), ratio=(0.95, 1.05)),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize(infer.IMG_MEAN, infer.IMG_STD),
])
PLAIN = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor(), transforms.Normalize(infer.IMG_MEAN, infer.IMG_STD)])


class Faces(Dataset):
    def __init__(self, items, tf):
        self.items, self.tf = items, tf

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        path, label = self.items[i]
        return self.tf(Image.open(path).convert("RGB")), torch.tensor(float(label))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--batch", type=int, default=16)
    args = parser.parse_args()
    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
    torch.set_num_threads(8)

    files, labels = list_split("train")
    items = list(zip(files, labels.tolist()))
    random.shuffle(items)
    hold = len(items) // 10  # 10% of TRAIN for monitoring; the test split stays untouched
    val_items, train_items = items[:hold], items[hold:]
    train = DataLoader(Faces(train_items, AUG), batch_size=args.batch, shuffle=True, num_workers=0)
    val = DataLoader(Faces(val_items, PLAIN), batch_size=32, num_workers=0)

    base = original_checkpoints()[args.fold - 1]
    model = load_classifier(base)
    for p in model.parameters():
        p.requires_grad = False
    trainable = [model.backbone.stages[-1], model.head]
    if hasattr(model.backbone, "head"):
        trainable.append(model.backbone.head)  # final norm inside timm's ConvNeXt head
    for module in trainable:
        for p in module.parameters():
            p.requires_grad = True
    params = [p for p in model.parameters() if p.requires_grad]
    print(f"trainable params: {sum(p.numel() for p in params)/1e6:.1f}M / {sum(p.numel() for p in model.parameters())/1e6:.1f}M", flush=True)
    opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.05)
    steps = args.epochs * len(train)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr, total_steps=steps, pct_start=0.1)
    loss_fn = torch.nn.BCEWithLogitsLoss()

    def validate():
        model.eval()
        correct = total = 0
        with torch.no_grad():
            for x, y in val:
                pred = (torch.sigmoid(model(x).squeeze(1)) >= 0.5).float()
                correct += int((pred == y).sum()); total += len(y)
        return correct / max(total, 1)

    history = [{"step": 0, "val_acc": validate()}]
    print(f"step 0 val_acc {history[0]['val_acc']:.3f}", flush=True)
    step, t0 = 0, time.time()
    for epoch in range(args.epochs):
        for x, y in train:
            model.train()
            # Keep frozen early stages in eval mode (no stochastic depth drift there).
            model.backbone.stages[:-1].eval()
            loss = loss_fn(model(x).squeeze(1), y)
            opt.zero_grad(); loss.backward(); opt.step(); sched.step()
            step += 1
            if step % 25 == 0 or step == steps:
                rate = step / (time.time() - t0)
                print(f"epoch {epoch+1} step {step}/{steps} loss {loss.item():.4f} ({rate:.2f} it/s, eta {(steps-step)/rate/60:.1f} min)", flush=True)
            if step % 100 == 0 or step == steps:
                history.append({"step": step, "val_acc": validate()})
                print(f"  val_acc {history[-1]['val_acc']:.3f}", flush=True)

    CKPT.mkdir(exist_ok=True)
    original = torch.load(base, map_location="cpu")
    out = CKPT / f"convnext_fold{args.fold}_gan.pt"
    torch.save({
        **{k: v for k, v in original.items() if k != "state_dict"},
        "state_dict": {k: v.half() if torch.is_floating_point(v) else v for k, v in model.state_dict().items()},
        "finetune": {"base": base.name, "data": "140k Real and Fake Faces (FFHQ vs StyleGAN) slice", "epochs": args.epochs,
                     "lr": args.lr, "train_images": len(train_items), "trainable": "stages[-1]+head", "history": history},
    }, out)
    print(f"saved {out} in {(time.time()-t0)/60:.1f} min", flush=True)
    (CKPT / f"convnext_fold{args.fold}_gan.history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
