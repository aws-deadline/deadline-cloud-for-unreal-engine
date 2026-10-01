#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "UObject/ObjectMacros.h"
#include "DeadlineCloudHiddenParameters.generated.h"

DECLARE_DELEGATE_RetVal(TSet<FName>, FGetHiddenNamesDelegate);
DECLARE_DELEGATE(FHiddenChangedDelegate);

USTRUCT()
struct FHiddenItemsManager
{
	GENERATED_BODY()

    UPROPERTY()
    TSet<FName> Hidden;

    FGetHiddenNamesDelegate OnGetAllNames;
    FGetHiddenNamesDelegate OnGetDefaultHidden;
    FHiddenChangedDelegate OnChanged;

    bool Contains(FName Name) const { return Hidden.Contains(Name); }
    bool IsEmpty() const { return Hidden.IsEmpty(); }
    TArray<FName> AsArray() const { return Hidden.Array(); }
    TSet<FName>  AsSet() const { return Hidden; }

    void Add(FName Name)
    {
        Hidden.Add(Name);
        Changed();
    }

    void Remove(FName Name)
    {
        Hidden.Remove(Name);
        Changed();
    }

    void Clear()
    {
        Hidden.Empty();
        Changed();
    }

    void ResetToDefault()
    {
        Hidden = OnGetDefaultHidden.IsBound() ? OnGetDefaultHidden.Execute() : TSet<FName>{};
        Changed();
    }

    bool IsDefaultState() const;

    bool IsDefaultForParameter(FName Name) const;

    void PruneUnknown();

private:
    void Changed()
    {
        if (OnChanged.IsBound())
        {
            OnChanged.Execute();
        }
    }
};