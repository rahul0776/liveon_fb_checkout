"use client";

export function BorderBeam() {
    return (
        <div className="absolute inset-0 rounded-lg overflow-hidden pointer-events-none">
            <div className="absolute inset-0 animate-border-beam">
                <div className="absolute inset-[-1px] rounded-lg border border-transparent bg-gradient-to-r from-transparent via-[#f6c35d] to-transparent bg-[length:200%_100%]" />
            </div>
        </div>
    );
}
