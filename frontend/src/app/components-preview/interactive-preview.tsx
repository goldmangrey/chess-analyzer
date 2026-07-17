"use client";

import { Check, Save, Sparkles } from "lucide-react";
import { useState } from "react";

import {
  Button,
  Modal,
  ToastProvider,
  useToast,
} from "@/components/ui";

function InteractiveControls() {
  const [modalOpen, setModalOpen] = useState(false);
  const { toast } = useToast();

  return (
    <div className="flex flex-wrap gap-3">
      <Button leftIcon={<Sparkles size={17} />} onClick={() => setModalOpen(true)}>
        Открыть Modal
      </Button>
      <Button
        variant="secondary"
        leftIcon={<Check size={17} />}
        onClick={() => toast({ title: "Готово", description: "Успешное уведомление", tone: "success" })}
      >
        Success toast
      </Button>
      <Button
        variant="secondary"
        onClick={() => toast({ title: "Не удалось сохранить", description: "Пример сообщения об ошибке", tone: "error" })}
      >
        Error toast
      </Button>
      <Button
        variant="ghost"
        onClick={() => toast({ title: "Локальный режим", tone: "info" })}
      >
        Info toast
      </Button>
      <Button
        variant="ghost"
        onClick={() => toast({ title: "Требуется внимание", tone: "warning" })}
      >
        Warning toast
      </Button>

      <Modal
        open={modalOpen}
        onOpenChange={setModalOpen}
        title="Подтвердить действие"
        description="Демонстрационный диалог не изменяет данные проекта."
        footer={
          <>
            <Button variant="ghost" onClick={() => setModalOpen(false)}>Отмена</Button>
            <Button leftIcon={<Save size={16} />} onClick={() => setModalOpen(false)}>Подтвердить</Button>
          </>
        }
      >
        <p className="text-sm leading-6 text-text-secondary">
          Escape, backdrop и кнопка закрытия завершают диалог. Tab остаётся внутри модального окна.
        </p>
      </Modal>
    </div>
  );
}

export function InteractivePreview() {
  return (
    <ToastProvider>
      <InteractiveControls />
    </ToastProvider>
  );
}
