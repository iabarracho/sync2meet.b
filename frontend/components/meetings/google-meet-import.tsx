"use client";



import { useRef, useState } from "react";

import { FileVideo, FileText, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";

import { api } from "@/lib/api";



type Props = {

  meetingId: string;

  disabled?: boolean;

  onSuccess: (message: string) => void;

  onError: (message: string) => void;

  onImported?: () => void;

};



const RECORDING_ACCEPT =

  ".mp4,.m4a,.mov,.webm,.mkv,.mp3,.wav,video/mp4,video/quicktime,video/webm,audio/webm,audio/mpeg";

const TRANSCRIPT_ACCEPT = ".vtt,.txt,.docx,.srt,.sbv";



export function GoogleMeetImport({

  meetingId,

  disabled,

  onSuccess,

  onError,

  onImported,

}: Props) {

  const recordingInputRef = useRef<HTMLInputElement>(null);

  const transcriptInputRef = useRef<HTMLInputElement>(null);

  const [loading, setLoading] = useState<"recording" | "transcript" | null>(null);



  const handleFile = async (

    file: File,

    mode: "recording" | "transcript"

  ) => {

    setLoading(mode);

    onError("");

    try {

      const result = await api.meetings.importGoogleMeet(meetingId, file, mode);

      onSuccess(result.message);

      onImported?.();

    } catch (err) {

      let msg =

        err instanceof Error

          ? err.message

          : "Falha ao importar ficheiro";

      if (

        msg.includes("ECONNREFUSED") ||

        msg.includes("Failed to fetch") ||

        msg.includes("fetch failed")

      ) {

        msg =

          "API offline (porta 8000). Corre ARRANCAR.cmd na pasta do projeto.";

      }

      onError(msg);

    } finally {

      setLoading(null);

    }

  };



  return (

    <div className="rounded-lg border border-blue-200 bg-blue-50/80 p-4 space-y-3">

      <div>

        <p className="text-sm font-semibold text-blue-900">

          Gravação da reunião (Google Meet)

        </p>

        <ol className="mt-2 list-decimal space-y-1 pl-4 text-xs text-blue-900/90">

          <li>

            Na call, grava com extensão que inclua{" "}

            <strong>áudio do separador + microfone</strong> (não só um dos dois).

          </li>

          <li>

            No fim, <strong>descarrega</strong> o ficheiro (MP4, WEBM ou MP3).

          </li>

          <li>

            Clica abaixo em <strong>Carregar gravação</strong> e escolhe o

            ficheiro.

          </li>

          <li>Depois: <strong>Transcrever</strong> → <strong>Gerar ata</strong>.</li>

        </ol>

        <p className="mt-2 text-xs text-blue-800/80">

          Dica: usa <strong>auscultadores</strong> para evitar eco. Antes de gravar,

          testa 10 segundos e confirma que ouves <em>tu e os outros</em> no vídeo

          descarregado.

        </p>

      </div>



      <div className="flex flex-wrap gap-2">

        <input

          ref={recordingInputRef}

          type="file"

          className="hidden"

          accept={RECORDING_ACCEPT}

          disabled={disabled || !!loading}

          onChange={(e) => {

            const file = e.target.files?.[0];

            if (file) handleFile(file, "recording");

            e.target.value = "";

          }}

        />

        <input

          ref={transcriptInputRef}

          type="file"

          className="hidden"

          accept={TRANSCRIPT_ACCEPT}

          disabled={disabled || !!loading}

          onChange={(e) => {

            const file = e.target.files?.[0];

            if (file) handleFile(file, "transcript");

            e.target.value = "";

          }}

        />

        <Button

          type="button"

          variant="outline"

          className="border-blue-300 bg-white hover:bg-blue-50"

          disabled={disabled || loading === "recording"}

          onClick={() => recordingInputRef.current?.click()}

        >

          <FileVideo className="h-4 w-4" />

          {loading === "recording"

            ? "A carregar…"

            : "Carregar gravação (MP4, WEBM…)"}

        </Button>

        <Button

          type="button"

          variant="outline"

          className="border-blue-300 bg-white hover:bg-blue-50"

          disabled={disabled || loading === "transcript"}

          onClick={() => transcriptInputRef.current?.click()}

        >

          <FileText className="h-4 w-4" />

          {loading === "transcript"

            ? "A carregar…"

            : "Carregar transcrição (VTT, DOCX…)"}

        </Button>

      </div>

      <p className="text-xs text-blue-700 flex items-center gap-1">

        <Upload className="h-3 w-3" />

        Formatos aceites: MP4, MOV, WEBM, MP3, WAV · ou transcrição VTT, TXT,

        DOCX, SRT

      </p>

    </div>

  );

}


