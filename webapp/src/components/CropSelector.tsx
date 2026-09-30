import { useQuery } from "@tanstack/react-query"

import { LoadingState } from "@/components/LoadingState"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { getCropCatalog } from "@/lib/api"

export interface CropSelectorValue {
  cropName: string
  variety: string
  stage: string
}

export function CropSelector({
  value,
  onChange,
}: {
  value: CropSelectorValue
  onChange: (value: CropSelectorValue) => void
}) {
  const { data: crops, isLoading } = useQuery({ queryKey: ["crop-catalog"], queryFn: getCropCatalog })

  if (isLoading || !crops) return <LoadingState label="Loading crop catalog..." />

  const selectedCrop = crops.find((c) => c.name === value.cropName)

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label>Crop</Label>
        <Select
          value={value.cropName}
          onValueChange={(cropName) => {
            const crop = crops.find((c) => c.name === cropName)
            onChange({ cropName: cropName ?? "", variety: crop?.varieties[0] ?? "", stage: crop?.stages[0] ?? "" })
          }}
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select a crop" />
          </SelectTrigger>
          <SelectContent>
            {crops.map((crop) => (
              <SelectItem key={crop.name} value={crop.name}>
                {crop.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {selectedCrop && (
        <>
          <div className="space-y-1.5">
            <Label>Variety</Label>
            <Select value={value.variety} onValueChange={(variety) => onChange({ ...value, variety: variety ?? "" })}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select a variety" />
              </SelectTrigger>
              <SelectContent>
                {selectedCrop.varieties.map((variety) => (
                  <SelectItem key={variety} value={variety}>
                    {variety}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>Current stage</Label>
            <Select value={value.stage} onValueChange={(stage) => onChange({ ...value, stage: stage ?? "" })}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select a stage" />
              </SelectTrigger>
              <SelectContent>
                {selectedCrop.stages.map((stage) => (
                  <SelectItem key={stage} value={stage}>
                    {stage}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </>
      )}
    </div>
  )
}
